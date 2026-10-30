#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <stdbool.h>
#include "common.h"

#define EPSILON 1e-9

#define NUMPY_TRACE_N65_P05 62864.0

static int failures = 0;

static void report(bool ok, const char *name) {
    if (ok) {
        printf("    [PASS] %s\n", name);
    } else {
        printf("    [FAIL] %s\n", name);
        failures++;
    }
}

static bool are_matrices_equal(int n, double **M1, double **M2) {
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            if (fabs(M1[i][j] - M2[i][j]) > EPSILON) {
                printf("      [Discrepancy in (%d,%d)]: M1=%.6f vs M2=%.6f\n", i, j, M1[i][j], M2[i][j]);
                return false;
            }
        }
    }
    return true;
}

static bool is_zero_matrix(int n, double **M) {
    for (int i = 0; i < n; i++)
        for (int j = 0; j < n; j++)
            if (M[i][j] != 0.0) return false;
    return true;
}

static void generate(int n, double p, double **A, double **B) {
    generate_matrices(n, p, A, B, NULL, NULL, NULL);
}

static double trace(int n, double **M) {
    double t = 0.0;
    for (int i = 0; i < n; i++) t += M[i][i];
    return t;
}
static void cross_validate(int n, int block_size, double p, const char *label) {
    double **A = allocate_matrix(n), **B = allocate_matrix(n);
    double **C_ref = allocate_matrix(n), **C_loop = allocate_matrix(n);
    double **C_tile = allocate_matrix(n), **C_sparse = allocate_matrix(n);

    generate(n, p, A, B);
    CSRMatrix *B_csr = create_csr_from_dense(n, B);

    multiply_baseline(n, A, B, C_ref);
    multiply_loop(n, A, B, C_loop);
    multiply_tile(n, A, B, C_tile, block_size);
    multiply_dense_csr(n, A, B_csr, C_sparse);

    char msg[160];
    snprintf(msg, sizeof msg, "%s: loop reordering == baseline", label);
    report(are_matrices_equal(n, C_ref, C_loop), msg);
    snprintf(msg, sizeof msg, "%s: tiling (block %d) == baseline", label, block_size);
    report(are_matrices_equal(n, C_ref, C_tile), msg);
    snprintf(msg, sizeof msg, "%s: sparse CSR == baseline", label);
    report(are_matrices_equal(n, C_ref, C_sparse), msg);

    free_csr(B_csr);
    free_matrix(n, A); free_matrix(n, B); free_matrix(n, C_ref);
    free_matrix(n, C_loop); free_matrix(n, C_tile); free_matrix(n, C_sparse);
}

int main(void) {
    printf("=====================================================\n");
    printf("CROSS-VALIDATION AND EDGE-CASE TEST SUITE\n");
    printf("=====================================================\n\n");

    printf("--> TEST 1: Cross-validation (baseline vs loop vs tile vs sparse CSR)\n");
    cross_validate(64, 16, 0.5, "n=64,  block=16, p=0.5 (n multiple of block)");
    cross_validate(70, 16, 0.5, "n=70,  block=16, p=0.5 (n NOT multiple of block)");
    cross_validate(65, 64, 0.95, "n=65,  block=64, p=0.95 (very sparse, partial last block)");
    cross_validate(50, 128, 0.0, "n=50,  block=128, p=0.0 (block larger than n, dense)");
    printf("\n");

    printf("--> TEST 2: Identity matrix (A x I = A)\n");
    {
        int n = 64;
        double **A = allocate_matrix(n), **I = allocate_matrix(n);
        double **C_dense = allocate_matrix(n), **C_sparse = allocate_matrix(n);
        for (int i = 0; i < n; i++)
            for (int j = 0; j < n; j++) {
                A[i][j] = (double)(i + j + 1);
                I[i][j] = (i == j) ? 1.0 : 0.0;
            }
        CSRMatrix *I_csr = create_csr_from_dense(n, I);
        multiply_baseline(n, A, I, C_dense);
        multiply_dense_csr(n, A, I_csr, C_sparse);
        report(are_matrices_equal(n, A, C_dense), "dense: A x I returns exactly A");
        report(are_matrices_equal(n, A, C_sparse), "sparse CSR: A x I returns exactly A");
        free_csr(I_csr);
        free_matrix(n, A); free_matrix(n, I); free_matrix(n, C_dense); free_matrix(n, C_sparse);
    }
    printf("\n");

    printf("--> TEST 3: Zero matrix (A x 0 = 0)\n");
    {
        int n = 64;
        double **A = allocate_matrix(n), **Z = allocate_matrix(n);
        double **C_base = allocate_matrix(n), **C_loop = allocate_matrix(n);
        double **C_tile = allocate_matrix(n), **C_sparse = allocate_matrix(n);
        for (int i = 0; i < n; i++)
            for (int j = 0; j < n; j++) {
                A[i][j] = (double)(i * 2 + j + 1);
                Z[i][j] = 0.0;
                C_base[i][j] = C_loop[i][j] = C_tile[i][j] = C_sparse[i][j] = 123.0;
            }
        CSRMatrix *Z_csr = create_csr_from_dense(n, Z);
        multiply_baseline(n, A, Z, C_base);
        multiply_loop(n, A, Z, C_loop);
        multiply_tile(n, A, Z, C_tile, 16);
        multiply_dense_csr(n, A, Z_csr, C_sparse);
        report(is_zero_matrix(n, C_base), "baseline returns a zero matrix");
        report(is_zero_matrix(n, C_loop), "loop reordering returns a zero matrix");
        report(is_zero_matrix(n, C_tile), "tiling returns a zero matrix");
        report(is_zero_matrix(n, C_sparse), "sparse CSR returns a zero matrix (and CSR has 0 nonzeros)");
        report(Z_csr->non_zeros == 0, "CSR of the zero matrix stores 0 nonzeros");
        free_csr(Z_csr);
        free_matrix(n, A); free_matrix(n, Z); free_matrix(n, C_base);
        free_matrix(n, C_loop); free_matrix(n, C_tile); free_matrix(n, C_sparse);
    }
    printf("\n");

    printf("--> TEST 4: Known small answer (2x2, computed by hand)\n");
    {
        int n = 2;
        double **A = allocate_matrix(n), **B = allocate_matrix(n);
        double **C = allocate_matrix(n), **E = allocate_matrix(n);
        A[0][0] = 1; A[0][1] = 2; A[1][0] = 3; A[1][1] = 4;
        B[0][0] = 5; B[0][1] = 6; B[1][0] = 7; B[1][1] = 8;
        E[0][0] = 19; E[0][1] = 22; E[1][0] = 43; E[1][1] = 50;
        multiply_baseline(n, A, B, C);
        report(are_matrices_equal(n, E, C), "[[1,2],[3,4]] x [[5,6],[7,8]] = [[19,22],[43,50]]");
        free_matrix(n, A); free_matrix(n, B); free_matrix(n, C); free_matrix(n, E);
    }
    printf("\n");

    printf("--> TEST 5: Independent reference (NumPy trace, n=65, p=0.5)\n");
    {
        int n = 65;
        double **A = allocate_matrix(n), **B = allocate_matrix(n);
        double **C_loop = allocate_matrix(n), **C_sparse = allocate_matrix(n);
        generate(n, 0.5, A, B);
        CSRMatrix *B_csr = create_csr_from_dense(n, B);
        multiply_loop(n, A, B, C_loop);
        multiply_dense_csr(n, A, B_csr, C_sparse);
        report(fabs(trace(n, C_loop) - NUMPY_TRACE_N65_P05) < EPSILON, "loop reordering trace matches NumPy");
        report(fabs(trace(n, C_sparse) - NUMPY_TRACE_N65_P05) < EPSILON, "sparse CSR trace matches NumPy");
        free_csr(B_csr);
        free_matrix(n, A); free_matrix(n, B); free_matrix(n, C_loop); free_matrix(n, C_sparse);
    }
    printf("\n");

    printf("=====================================================\n");
    if (failures == 0) {
        printf(" SUCCESS: ALL TESTS PASSED\n");
    } else {
        printf(" FAILURE: %d CHECK(S) FAILED\n", failures);
    }
    printf("=====================================================\n");
    return failures == 0 ? 0 : EXIT_FAILURE;
}