#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <math.h>
#include "common.h"

int main(int argc, char *argv[]) {
    if (argc < 4) {
        fprintf(stderr, "Usage: %s <matrix_size> <variant: ikj|tile> <threads> [block_size]\n", argv[0]);
        return EXIT_FAILURE;
    }

    int n = atoi(argv[1]);
    char *variant = argv[2];
    int requested_threads = atoi(argv[3]);
    int block_size = (argc > 4) ? atoi(argv[4]) : 64;

    double **A = allocate_matrix(n);
    double **B = allocate_matrix(n);
    double **C = allocate_matrix(n);

    int nnz_a = 0, nnz_b = 0;
    generate_matrices(n, 0.0, A, B, C, &nnz_a, &nnz_b);

    int actual_threads = 1;
#ifdef _OPENMP
    if (requested_threads > 0) {
        omp_set_num_threads(requested_threads);
    }
    #pragma omp parallel
    {
        #pragma omp single
        {
            actual_threads = omp_get_num_threads();
        }
    }
#else
    actual_threads = 1;
#endif

    if (strcmp(variant, "tile") == 0) {
        multiply_tile_parallel(n, A, B, C, block_size, requested_threads);
    } else {
        multiply_loop_parallel(n, A, B, C, requested_threads);
    }

    struct timespec start, end;
    clock_gettime(CLOCK_MONOTONIC, &start);

    if (strcmp(variant, "tile") == 0) {
        multiply_tile_parallel(n, A, B, C, block_size, requested_threads);
    } else {
        multiply_loop_parallel(n, A, B, C, requested_threads);
    }

    clock_gettime(CLOCK_MONOTONIC, &end);
    double elapsed = (end.tv_sec - start.tv_sec) + (end.tv_nsec - start.tv_nsec) / 1e9;

    int nnz_c = 0;
    double checksum_trace = 0.0;
    double checksum_full = 0.0;
    for (int i = 0; i < n; i++) {
        checksum_trace += C[i][i];
        for (int j = 0; j < n; j++) {
            checksum_full += C[i][j];
            if (C[i][j] != 0.0) nnz_c++;
        }
    }

    size_t peak_mem_kb = get_peak_memory_kb();

    printf("PARALLEL_MATMUL: variant = %s | RequestedThreads = %d | ActualThreads = %d | n = %d | NNZ(A) = %d | NNZ(B) = %d | NNZ(C) = %d | Time = %.6f seconds | PeakMemory = %zu KB | Checksum = %.4f\n",
            variant, requested_threads, actual_threads, n, nnz_a, nnz_b, nnz_c, elapsed, peak_mem_kb, checksum_full);

    free_matrix(n, A);
    free_matrix(n, B);
    free_matrix(n, C);

    return 0;
}