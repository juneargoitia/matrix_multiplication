#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <math.h>
#include "common.h"

int main(int argc, char *argv[]) {
    if (argc < 2) {
        fprintf(stderr, "Usage: %s <matrix_size> [sparsity_threshold_0_to_1]\n", argv[0]);
        return EXIT_FAILURE;
    }

    int n = atoi(argv[1]);
    double sparsity_target = (argc > 2) ? atof(argv[2]) : 0.8;

    double **A = allocate_matrix(n);
    double **B_dense = allocate_matrix(n);
    double **C = allocate_matrix(n);

    int nnz_a = 0, nnz_b = 0;

    generate_matrices(n, sparsity_target, A, B_dense, C, &nnz_a, &nnz_b);

    struct timespec conv_start, conv_end;
    clock_gettime(CLOCK_MONOTONIC, &conv_start);
    CSRMatrix *B_csr = create_csr_from_dense(n, B_dense);
    clock_gettime(CLOCK_MONOTONIC, &conv_end);
    double conversion_time = (conv_end.tv_sec - conv_start.tv_sec) + (conv_end.tv_nsec - conv_start.tv_nsec) / 1e9;

    free_matrix(n, B_dense);

    multiply_dense_csr(n, A, B_csr, C);

    struct timespec start, end;
    clock_gettime(CLOCK_MONOTONIC, &start);
    multiply_dense_csr(n, A, B_csr, C);
    clock_gettime(CLOCK_MONOTONIC, &end);
    double elapsed = (end.tv_sec - start.tv_sec) + (end.tv_nsec - start.tv_nsec) / 1e9;

    int nnz_c = 0;
    double checksum = 0.0;
    for (int i = 0; i < n; i++) {
        checksum += C[i][i];
        for (int j = 0; j < n; j++) {
            if (C[i][j] != 0.0) nnz_c++;
        }
    }

    size_t peak_mem_kb = get_peak_memory_kb();

    printf("SPARSE CSR: n = %d | TargetSparsity = %.2f | NNZ(A) = %d | NNZ(B) = %d | NNZ(C) = %d | ConvTime = %.6f seconds | MultTime = %.6f seconds | PeakMemory = %zu KB | Checksum = %.4f\n", 
                n, sparsity_target, nnz_a, nnz_b, nnz_c, conversion_time, elapsed, peak_mem_kb, checksum);

    free_matrix(n, A);
    free_matrix(n, C);
    free_csr(B_csr);

    return 0;
}