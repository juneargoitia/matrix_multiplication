#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <assert.h>
#include <stdbool.h>

#define EPSILON 1e-9

typedef struct {
    int rows;
    int cols;
    int non_zeros;
    double *values;
    int *col_indices;
    int *row_ptr;
} CSRMatrix;

double** allocate_matrix(int n) {
    double **matrix = (double **)malloc(n * sizeof(double *));
    if (!matrix) exit(EXIT_FAILURE);
    for (int i = 0; i < n; i++) {
        matrix[i] = (double *)calloc(n, sizeof(double));
        if (!matrix[i]) exit(EXIT_FAILURE);
    }
    return matrix;
}

void free_matrix(int n, double **matrix) {
    for (int i = 0; i < n; i++) free(matrix[i]);
    free(matrix);
}

CSRMatrix* create_csr_from_dense(int n, double **dense) {
    CSRMatrix *csr = (CSRMatrix *)malloc(sizeof(CSRMatrix));
    csr->rows = n;
    csr->cols = n;

    int nnz = 0;
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            if (dense[i][j] != 0.0) nnz++;
        }
    }
    csr->non_zeros = nnz;

    csr->values = (double *)malloc(nnz * sizeof(double));
    csr->col_indices = (int *)malloc(nnz * sizeof(int));
    csr->row_ptr = (int *)malloc((n + 1) * sizeof(int));

    int current = 0;
    csr->row_ptr[0] = 0;
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            if (dense[i][j] != 0.0) {
                csr->values[current] = dense[i][j];
                csr->col_indices[current] = j;
                current++;
            }
        }
        csr->row_ptr[i + 1] = current;
    }
    return csr;
}

void free_csr(CSRMatrix *csr) {
    free(csr->values);
    free(csr->col_indices);
    free(csr->row_ptr);
    free(csr);
}

void multiply_baseline(int n, double **A, double **B, double **C) {
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            C[i][j] = 0.0;
            for (int k = 0; k < n; k++) {
                C[i][j] += A[i][k] * B[k][j];
            }
        }
    }
}

void multiply_loop(int n, double **A, double **B, double **C) {
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) C[i][j] = 0.0;
    }
    for (int i = 0; i < n; i++) {
        for (int k = 0; k < n; k++) {
            double a_ik = A[i][k];
            for (int j = 0; j < n; j++) {
                C[i][j] += a_ik * B[k][j];
            }
        }
    }
}

void multiply_tile(int n, double **A, double **B, double **C, int block_size) {
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) C[i][j] = 0.0;
    }
    for (int ii = 0; ii < n; ii += block_size) {
        for (int kk = 0; kk < n; kk += block_size) {
            for (int jj = 0; jj < n; jj += block_size) {
                int i_max = (ii + block_size < n) ? ii + block_size : n;
                int k_max = (kk + block_size < n) ? kk + block_size : n;
                int j_max = (jj + block_size < n) ? jj + block_size : n;

                for (int i = ii; i < i_max; i++) {
                    for (int k = kk; k < k_max; k++) {
                        double a_ik = A[i][k];
                        for (int j = jj; j < j_max; j++) {
                            C[i][j] += a_ik * B[k][j];
                        }
                    }
                }
            }
        }
    }
}

void multiply_sparse_csr(int n, double **A, CSRMatrix *B, double **C) {
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) C[i][j] = 0.0;
    }
    for (int i = 0; i < n; i++) {
        for (int k = 0; k < n; k++) {
            double a_ik = A[i][k];
            if (a_ik != 0.0) {
                int start = B->row_ptr[k];
                int end = B->row_ptr[k + 1];
                for (int idx = start; idx < end; idx++) {
                    int j = B->col_indices[idx];
                    C[i][j] += a_ik * B->values[idx];
                }
            }
        }
    }
}


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
    printf("=====================================================\n");
    printf("COMPLETE SUITE FOR CROSS-VALIDATION AND EDGE CASES\n");
    printf("=====================================================\n\n");

    double **A = allocate_matrix(n);
    double **B = allocate_matrix(n);
    double **C_ref = allocate_matrix(n);
    double **C_loop = allocate_matrix(n);
    double **C_tile = allocate_matrix(n);
    double **C_sparse = allocate_matrix(n);

    printf("--> TEST 1: Cross-Validation (Baseline vs Loop vs Tile vs Sparse CSR)\n");
    srand(42);
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            A[i][j] = ((double)(rand() % 10) + 1.0);
            B[i][j] = ((double)rand() / RAND_MAX > 0.5) ? ((double)(rand() % 10) + 1.0) : 0.0;
        }
    }

    CSRMatrix *B_csr = create_csr_from_dense(n, B);

    multiply_baseline(n, A, B, C_ref);
    multiply_loop(n, A, B, C_loop);
    multiply_tile(n, A, B, C_tile, 16);
    multiply_sparse_csr(n, A, B_csr, C_sparse);

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
            B[i][j] = (i == j) ? 1.0 : 0.0;
        }
    }

    CSRMatrix *I_csr = create_csr_from_dense(n, B);
    multiply_sparse_csr(n, A, I_csr, C_sparse);

    if (are_matrices_equal(n, A, C_sparse)) {
        printf("    [PASS] Verification successful: A x I returns exactly A.\n\n");
    } else {
        printf("    [FAIL] Failure in the identity matrix test.\n\n");
        exit(EXIT_FAILURE);
    }
    free_csr(I_csr);

    printf("--> TEST 3: Case Border - Zero Matrix Property (A x 0 = 0)\n");
    double **Zero = allocate_matrix(n);
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            A[i][j] = (double)(i * 2 + j);
            B[i][j] = 0.0;
        }
    }

    multiply_tile(n, A, B, C_tile, 16);

    if (are_matrices_equal(n, Zero, C_tile)) {
        printf("    [PASS] Verification successful: Multiplication by zero produces a zero matrix.\n\n");
    } else {
        printf("    [FAIL] Failure in the zero-matrix test.\n\n");
        exit(EXIT_FAILURE);
    }

    free_matrix(n, A);
    free_matrix(n, B);
    free_matrix(n, C_ref);
    free_matrix(n, C_loop);
    free_matrix(n, C_tile);
    free_matrix(n, C_sparse);
    free_matrix(n, Zero);

    printf("=====================================================\n");
    printf(" SUCCESS: ALL TESTS WERE COMPLETED SUCCESSFULLY\n");
    printf("=====================================================\n");

    return 0;
}