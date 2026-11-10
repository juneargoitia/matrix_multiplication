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
    printf("ASSIGNMENT 3: PARALLEL CORRECTNESS & VERIFICATION SUITE\n");
    printf("=====================================================\n\n");

    int n = 64;
    double **A = allocate_matrix(n);
    double **B = allocate_matrix(n);
    double **C_seq = allocate_matrix(n);
    double **C_par = allocate_matrix(n);

    generate_matrices(n, 0.0, A, B, NULL, NULL, NULL);

    multiply_loop_parallel(n, A, B, C_seq, 1);

    int test_threads[] = {1, 2, 4, 8};
    for (int t = 0; t < 4; t++) {
        int th = test_threads[t];
        multiply_loop_parallel(n, A, B, C_par, th);
        char msg[128];
        snprintf(msg, sizeof(msg), "ikj parallel (threads=%d) matches sequential baseline", th);
        report(are_matrices_equal(n, C_seq, C_par), msg);

        multiply_tile_parallel(n, A, B, C_par, 16, th);
        snprintf(msg, sizeof(msg), "tile parallel B=16 (threads=%d) matches sequential baseline", th);
        report(are_matrices_equal(n, C_seq, C_par), msg);
    }

    free_matrix(n, A);
    free_matrix(n, B);
    free_matrix(n, C_seq);
    free_matrix(n, C_par);

    printf("\n=====================================================\n");
    if (failures == 0) {
        printf(" SUCCESS: ALL PARALLEL TESTS PASSED\n");
    } else {
        printf(" FAILURE: %d CHECK(S) FAILED\n", failures);
    }
    printf("=====================================================\n");
    return failures == 0 ? 0 : EXIT_FAILURE;
}