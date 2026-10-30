#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <math.h>
#include "common.h"

int main(int argc, char *argv[]) {
    if (argc < 2) {
        fprintf(stderr, "Usage: %s <matrix_size>\n", argv[0]);
        return EXIT_FAILURE;
    }

    int n = atoi(argv[1]);
    double **A = allocate_matrix(n);
    double **B = allocate_matrix(n);
    double **C = allocate_matrix(n);

    seed_xorshift32(42);
    int nnz_a = 0, nnz_b = 0;
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            A[i][j] = floor(random_double() * 10.0) + 1.0;
            B[i][j] = floor(random_double() * 10.0) + 1.0;
            if (A[i][j] != 0.0) nnz_a++;
            if (B[i][j] != 0.0) nnz_b++;
            C[i][j] = 0.0;
        }
    }

    multiply_baseline(n, A, B, C);

    struct timespec start, end;
    clock_gettime(CLOCK_MONOTONIC, &start);

    multiply_baseline(n, A, B, C);

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

    printf("BASELINE: n = %d | NNZ(A) = %d | NNZ(B) = %d | NNZ(C) = %d | Time = %.6f seconds | PeakMemory = %zu KB | Checksum = %.4f\n",
                n, nnz_a, nnz_b, nnz_c, elapsed, peak_mem_kb, checksum);

    free_matrix(n, A);
    free_matrix(n, B);
    free_matrix(n, C);

    return 0;
}