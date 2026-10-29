#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <assert.h>

#define EPSILON 1e-9

int verify_matrices(int n, double **C1, double **C2) {
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            if (fabs(C1[i][j] - C2[i][j]) > EPSILON) {
                return 0;
            }
        }
    }
    return 1;
}

int main() {
    int n = 100;
    printf("Running batteries of correctness tests for n = %d...\n", n);

    double **A = (double **)malloc(n * sizeof(double *));
    double **B = (double **)malloc(n * sizeof(double *));
    double **C_base = (double **)malloc(n * sizeof(double *));
    double **C_opt = (double **)malloc(n * sizeof(double *));

    for (int i = 0; i < n; i++) {
        A[i] = (double *)malloc(n * sizeof(double));
        B[i] = (double *)malloc(n * sizeof(double));
        C_base[i] = (double *)malloc(n * sizeof(double));
        C_opt[i] = (double *)malloc(n * sizeof(double));
    }

    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            A[i][j] = (double)((i + j) % 5 + 1.0);
            B[i][j] = (double)((i - j) % 5 + 1.0);
        }
    }

    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            C_base[i][j] = 0.0;
            for (int k = 0; k < n; k++) {
                C_base[i][j] += A[i][k] * B[k][j];
            }
        }
    }

    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) C_opt[i][j] = 0.0;
        for (int k = 0; k < n; k++) {
            for (int j = 0; j < n; j++) {
                C_opt[i][j] += A[i][k] * B[k][j];
            }
        }
    }

    if (verify_matrices(n, C_base, C_opt)) {
        printf("[OK] Test 1 passed: Baseline and Loop Reordering produce identical results.\n");
    } else {
        printf("[ERROR] Test 1 failed: Discrepancy between Baseline and Loop Reordering.\n");
        exit(1);
    }

    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            A[i][j] = 0.0;
            B[i][j] = (double)(i + 1);
            C_base[i][j] = 0.0;
        }
    }
    for (int i = 0; i < n; i++) {
        for (int k = 0; k < n; k++) {
            for (int j = 0; j < n; j++) {
                C_base[i][j] += A[i][k] * B[k][j];
            }
        }
    }
    int all_zeros = 1;
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            if (C_base[i][j] != 0.0) all_zeros = 0;
        }
    }
    if (all_zeros) {
        printf("[OK] Test 2 passed: Multiplication by zero matrix validated correctly.\n");
    } else {
        printf("[ERROR] Test 2 failed: The zero matrix did not return zeros.\n");
        exit(1);
    }

    for (int i = 0; i < n; i++) {
        free(A[i]); free(B[i]); free(C_base[i]); free(C_opt[i]);
    }
    free(A); free(B); free(C_base); free(C_opt);

    printf("\nSUCCESS: All correctness tests have been completed successfully.\n");
    return 0;
}