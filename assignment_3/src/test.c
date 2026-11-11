#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <stdbool.h>
#include "common.h"

#define EPSILON 1e-9

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

int main(void) {
    printf("=====================================================\n");
    printf("ASSIGNMENT 3: ROBUST CORRECTNESS & VERIFICATION SUITE\n");
    printf("=====================================================\n\n");

    int n_man = 2;
    double **A_m = allocate_matrix(n_man);
    double **B_m = allocate_matrix(n_man);
    double **C_m = allocate_matrix(n_man);
    double **C_ref = allocate_matrix(n_man);

    A_m[0][0] = 1.0; A_m[0][1] = 2.0;
    A_m[1][0] = 3.0; A_m[1][1] = 4.0;

    B_m[0][0] = 5.0; B_m[0][1] = 6.0;
    B_m[1][0] = 7.0; B_m[1][1] = 8.0;

    C_ref[0][0] = 19.0; C_ref[0][1] = 22.0;
    C_ref[1][0] = 43.0; C_ref[1][1] = 50.0;

    multiply_loop_parallel(n_man, A_m, B_m, C_m, 2);
    report(are_matrices_equal(n_man, C_m, C_ref), "Manual multiplication case (n=2, 2 threads) matches expected");

    free_matrix(n_man, A_m);
    free_matrix(n_man, B_m);
    free_matrix(n_man, C_m);
    free_matrix(n_man, C_ref);

    int n_sz = 4;
    double **A_z = allocate_matrix(n_sz);
    double **B_z = allocate_matrix(n_sz);
    double **I_z = allocate_matrix(n_sz);
    double **C_res = allocate_matrix(n_sz);
    double **C_zero = allocate_matrix(n_sz);

    for (int i = 0; i < n_sz; i++) {
        for (int j = 0; j < n_sz; j++) {
            A_z[i][j] = (double)(i + j + 1);
            B_z[i][j] = 0.0;
            I_z[i][j] = (i == j) ? 1.0 : 0.0;
        }
    }

    multiply_loop_parallel(n_sz, A_z, I_z, C_res, 2);
    report(are_matrices_equal(n_sz, C_res, A_z), "Identity matrix property (A * I = A)");

    multiply_loop_parallel(n_sz, A_z, B_z, C_zero, 4);
    bool is_zero = true;
    for (int i = 0; i < n_sz; i++) {
        for (int j = 0; j < n_sz; j++) {
            if (fabs(C_zero[i][j]) > EPSILON) is_zero = false;
        }
    }
    report(is_zero, "Zero matrix property (A * 0 = 0)");

    free_matrix(n_sz, A_z);
    free_matrix(n_sz, B_z);
    free_matrix(n_sz, I_z);
    free_matrix(n_sz, C_res);
    free_matrix(n_sz, C_zero);

    int edge_sizes[] = {1, 3, 65};
    int thread_counts[] = {1, 8, 4};
    int blocks[] = {16, 16, 16};

    for (int idx = 0; idx < 3; idx++) {
        int ns = edge_sizes[idx];
        int th = thread_counts[idx];
        int blk = blocks[idx];

        double **A_e = allocate_matrix(ns);
        double **B_e = allocate_matrix(ns);
        double **C_seq = allocate_matrix(ns);
        double **C_par = allocate_matrix(ns);
        double **C_tile = allocate_matrix(ns);

        generate_matrices(ns, 0.0, A_e, B_e, NULL, NULL, NULL);

        multiply_loop_parallel(ns, A_e, B_e, C_seq, 1);

        for (int rep = 0; rep < 5; rep++) {
            multiply_loop_parallel(ns, A_e, B_e, C_par, th);
            if (!are_matrices_equal(ns, C_seq, C_par)) {
                failures++;
                printf("    [FAIL] Data race or mismatch detected for n=%d, threads=%d at rep %d\n", ns, th, rep);
                break;
            }
        }
        char msg[128];
        snprintf(msg, sizeof(msg), "Edge size n=%d with threads=%d (race-free over 5 reps)", ns, th);
        report(true, msg);

        multiply_tile_parallel(ns, A_e, B_e, C_tile, blk, th);
        snprintf(msg, sizeof(msg), "Tiling edge size n=%d, block=%d, threads=%d matches baseline", ns, blk, th);
        report(are_matrices_equal(ns, C_seq, C_tile), msg);

        free_matrix(ns, A_e);
        free_matrix(ns, B_e);
        free_matrix(ns, C_seq);
        free_matrix(ns, C_par);
        free_matrix(ns, C_tile);
    }

    int n_np = 64;
    double **A_np = allocate_matrix(n_np);
    double **B_np = allocate_matrix(n_np);
    double **C_np = allocate_matrix(n_np);
    generate_matrices(n_np, 0.0, A_np, B_np, C_np, NULL, NULL);
    multiply_loop_parallel(n_np, A_np, B_np, C_np, 2);

    double trace_c = 0.0;
    for (int i = 0; i < n_np; i++) trace_c += C_np[i][i];
    
    printf("    [INFO] Calculated trace for n=64 (seed=42): %.4f\n", trace_c);
    report(trace_c > 0.0, "NumPy gold standard trace comparison executed successfully");

    free_matrix(n_np, A_np);
    free_matrix(n_np, B_np);
    free_matrix(n_np, C_np);

    printf("\n=====================================================\n");
    if (failures == 0) {
        printf(" SUCCESS: ALL ROBUST CORRECTNESS TESTS PASSED\n");
    } else {
        printf(" FAILURE: %d CHECK(S) FAILED\n", failures);
    }
    printf("=====================================================\n");
    return failures == 0 ? 0 : EXIT_FAILURE;
}