#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <stdbool.h>
#include "common.h"

#define EPSILON 1e-9

bool are_matrices_equal(int n, double **M1, double **M2) {
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            if (fabs(M1[i][j] - M2[i][j]) > EPSILON) {
                printf("  [Discrepancy in (%d,%d)]: M1=%.6f vs M2=%.6f\n", i, j, M1[i][j], M2[i][j]);
                return false;
            }
        }
    }
    return true;
}

int main() {
    int n = 64;
    int block_size = 16;

    printf("=====================================================\n");
    printf("COMPLETE SUITE FOR CROSS-VALIDATION AND EDGE CASES\n", n, block_size);
    printf("=====================================================\n\n");

    double **A = allocate_matrix(n);
    double **B_dense = allocate_matrix(n);
    double **C_ref = allocate_matrix(n);
    double **C_loop = allocate_matrix(n);
    double **C_tile = allocate_matrix(n);
    double **C_sparse = allocate_matrix(n);

    printf("--> TEST 1: Cross-Validation (Baseline vs Loop vs Tile vs Sparse CSR)\n");
    seed_xorshift32(42);
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            A[i][j] = floor(random_double() * 10.0) + 1.0;
            double val_b = floor(random_double() * 10.0) + 1.0;
            double prob = random_double();
            B_dense[i][j] = (prob >= 0.5) ? val_b : 0.0;
        }
    }

    CSRMatrix *B_csr = create_csr_from_dense(n, B_dense);

    multiply_baseline(n, A, B_dense, C_ref);
    multiply_loop(n, A, B_dense, C_loop);
    multiply_tile(n, A, B_dense, C_tile, block_size);
    multiply_dense_csr(n, A, B_csr, C_sparse);

    bool p1_loop = are_matrices_equal(n, C_ref, C_loop);
    bool p1_tile = are_matrices_equal(n, C_ref, C_tile);
    bool p1_sparse = are_matrices_equal(n, C_ref, C_sparse);

    if (p1_loop && p1_tile && p1_sparse) {
        printf("    [PASS] All 4 methods produce IDENTICAL matrices for arbitrary matrices.\n\n");
    } else {
        printf("    [FAIL] Cross-validation failure.\n\n");
        exit(EXIT_FAILURE);
    }
    free_csr(B_csr);

    printf("--> TEST 2: Case Border - Identity Matrix Property (A x I = A)\n");
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            A[i][j] = (double)(i + j + 1);
            B_dense[i][j] = (i == j) ? 1.0 : 0.0;
        }
    }

    CSRMatrix *I_csr = create_csr_from_dense(n, B_dense);
    multiply_dense_csr(n, A, I_csr, C_sparse);

    if (are_matrices_equal(n, A, C_sparse)) {
        printf("    [PASS] Verification successful: A x I returns exactly A.\n\n");
    } else {
        printf("    [FAIL] Failure in the identity matrix test.\n\n");
        exit(EXIT_FAILURE);
    }
    free_csr(I_csr);

    free_matrix(n, A);
    free_matrix(n, B_dense);
    free_matrix(n, C_ref);
    free_matrix(n, C_loop);
    free_matrix(n, C_tile);
    free_matrix(n, C_sparse);

    printf("=====================================================\n");
    printf(" SUCCESS: ALL TESTS WERE COMPLETED SUCCESSFULLY\n");
    printf("=====================================================\n");

    return 0;
}