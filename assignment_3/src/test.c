#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <stdbool.h>
#include "common.h"

#define EPSILON 1e-9
#define NUMPY_TRACE_N64 124175.0
#define NUMPY_SUM_N64   7926400.0

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

static void multiply_reference(int n, double **A, double **B, double **C) {
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            double s = 0.0;
            for (int k = 0; k < n; k++) s += A[i][k] * B[k][j];
            C[i][j] = s;
        }
    }
}

static void dirty(int n, double **C) {
    for (int i = 0; i < n; i++)
        for (int j = 0; j < n; j++) C[i][j] = 123.0;
}

static int actual_threads(int threads) {
    int t = 1;
#ifdef _OPENMP
    #pragma omp parallel num_threads(threads)
    {
        #pragma omp single
        t = omp_get_num_threads();
    }
#else
    (void)threads;
#endif
    return t;
}

int main(void) {
    printf("=====================================================\n");
    printf("ASSIGNMENT 3: ROBUST CORRECTNESS & VERIFICATION SUITE\n");
#ifdef _OPENMP
    printf("Build: OpenMP (_OPENMP = %d)\n", _OPENMP);
#else
    printf("Build: sequential (no OpenMP)\n");
#endif
    printf("=====================================================\n\n");

    char msg[160];
    const int th_list[] = {1, 2, 3, 4, 8};
    const int n_th = (int)(sizeof th_list / sizeof th_list[0]);

    printf("--> TEST 1: Known 2x2 answer\n");
    {
        int n = 2;
        double **A = allocate_matrix(n), **B = allocate_matrix(n);
        double **C = allocate_matrix(n), **E = allocate_matrix(n);
        A[0][0] = 1; A[0][1] = 2; A[1][0] = 3; A[1][1] = 4;
        B[0][0] = 5; B[0][1] = 6; B[1][0] = 7; B[1][1] = 8;
        E[0][0] = 19; E[0][1] = 22; E[1][0] = 43; E[1][1] = 50;
        for (int t = 0; t < n_th; t++) {
            dirty(n, C);
            multiply_loop_parallel(n, A, B, C, th_list[t]);
            snprintf(msg, sizeof msg, "ikj, threads=%d gives [[19,22],[43,50]]", th_list[t]);
            report(are_matrices_equal(n, E, C), msg);
            dirty(n, C);
            multiply_tile_parallel(n, A, B, C, 2, th_list[t]);
            snprintf(msg, sizeof msg, "tile, threads=%d gives [[19,22],[43,50]]", th_list[t]);
            report(are_matrices_equal(n, E, C), msg);
        }
        free_matrix(n, A); free_matrix(n, B); free_matrix(n, C); free_matrix(n, E);
    }
    printf("\n");

    printf("--> TEST 2: Identity (A x I = A) and zero (A x 0 = 0), both variants\n");
    {
        int n = 20;
        double **A = allocate_matrix(n), **I = allocate_matrix(n);
        double **Z = allocate_matrix(n), **C = allocate_matrix(n);
        for (int i = 0; i < n; i++)
            for (int j = 0; j < n; j++) {
                A[i][j] = (double)(i + 2 * j + 1);
                I[i][j] = (i == j) ? 1.0 : 0.0;
                Z[i][j] = 0.0;
            }
        for (int t = 0; t < n_th; t++) {
            int th = th_list[t];
            dirty(n, C); multiply_loop_parallel(n, A, I, C, th);
            snprintf(msg, sizeof msg, "ikj: A x I = A (threads=%d)", th);
            report(are_matrices_equal(n, A, C), msg);
            dirty(n, C); multiply_tile_parallel(n, A, I, C, 8, th);
            snprintf(msg, sizeof msg, "tile: A x I = A (threads=%d)", th);
            report(are_matrices_equal(n, A, C), msg);
            dirty(n, C); multiply_loop_parallel(n, A, Z, C, th);
            snprintf(msg, sizeof msg, "ikj: A x 0 = 0 (threads=%d)", th);
            report(is_zero_matrix(n, C), msg);
            dirty(n, C); multiply_tile_parallel(n, A, Z, C, 8, th);
            snprintf(msg, sizeof msg, "tile: A x 0 = 0 (threads=%d)", th);
            report(is_zero_matrix(n, C), msg);
        }
        free_matrix(n, A); free_matrix(n, I); free_matrix(n, Z); free_matrix(n, C);
    }
    printf("\n");

    printf("--> TEST 3: Edge sizes, all thread counts, repeated runs (race detection)\n");
    {
        const int sizes[]  = {1, 3, 7, 65, 70};
        const int blocks[] = {1, 16, 64};
        for (int s = 0; s < 5; s++) {
            int n = sizes[s];
            double **A = allocate_matrix(n), **B = allocate_matrix(n);
            double **C_ref = allocate_matrix(n), **C = allocate_matrix(n);
            generate_matrices(n, 0.0, A, B, NULL, NULL, NULL);
            multiply_reference(n, A, B, C_ref);

            for (int t = 0; t < n_th; t++) {
                int th = th_list[t];
                bool ok = true;
                for (int rep = 0; rep < 5 && ok; rep++) {
                    dirty(n, C);
                    multiply_loop_parallel(n, A, B, C, th);
                    ok = are_matrices_equal(n, C_ref, C);
                }
                snprintf(msg, sizeof msg, "ikj n=%d threads=%d == reference (5 runs, identical every time)", n, th);
                report(ok, msg);

                for (int b = 0; b < 3; b++) {
                    ok = true;
                    for (int rep = 0; rep < 3 && ok; rep++) {
                        dirty(n, C);
                        multiply_tile_parallel(n, A, B, C, blocks[b], th);
                        ok = are_matrices_equal(n, C_ref, C);
                    }
                    snprintf(msg, sizeof msg, "tile n=%d block=%d threads=%d == reference", n, blocks[b], th);
                    report(ok, msg);
                }
            }
            free_matrix(n, A); free_matrix(n, B); free_matrix(n, C_ref); free_matrix(n, C);
        }
    }
    printf("\n");

    printf("--> TEST 4: Independent NumPy reference (n=64, p=0.0)\n");
    {
        int n = 64;
        double **A = allocate_matrix(n), **B = allocate_matrix(n), **C = allocate_matrix(n);
        generate_matrices(n, 0.0, A, B, NULL, NULL, NULL);
        for (int t = 0; t < n_th; t++) {
            int th = th_list[t];
            for (int v = 0; v < 2; v++) {
                dirty(n, C);
                if (v == 0) multiply_loop_parallel(n, A, B, C, th);
                else        multiply_tile_parallel(n, A, B, C, 64, th);
                double tr = 0.0, sum = 0.0;
                for (int i = 0; i < n; i++) {
                    tr += C[i][i];
                    for (int j = 0; j < n; j++) sum += C[i][j];
                }
                snprintf(msg, sizeof msg, "%s threads=%d: trace=%.0f, sum=%.0f match NumPy",
                            v == 0 ? "ikj " : "tile", th, tr, sum);
                report(fabs(tr - NUMPY_TRACE_N64) < EPSILON && fabs(sum - NUMPY_SUM_N64) < EPSILON, msg);
            }
        }
        free_matrix(n, A); free_matrix(n, B); free_matrix(n, C);
    }
    printf("\n");

    printf("--> TEST 5: Requested vs actual thread count\n");
    for (int t = 0; t < n_th; t++) {
        int th = th_list[t];
        int got = actual_threads(th);
#ifdef _OPENMP
        int expected = th;
#else
        int expected = 1;
#endif
        snprintf(msg, sizeof msg, "requested=%d actual=%d (expected %d)", th, got, expected);
        report(got == expected, msg);
    }
    printf("\n");

    printf("=====================================================\n");
    if (failures == 0) {
        printf(" SUCCESS: ALL ROBUST CORRECTNESS TESTS PASSED\n");
    } else {
        printf(" FAILURE: %d CHECK(S) FAILED\n", failures);
    }
    printf("=====================================================\n");
    return failures == 0 ? 0 : EXIT_FAILURE;
}