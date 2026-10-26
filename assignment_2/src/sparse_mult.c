#include <stdio.h>
#include <stdlib.h>
#include <time.h>

typedef struct {
    int rows;
    int cols;
    int non_zeros;
    double *values;
    int *col_indices;
    int *row_ptr;
} CSRMatrix;

void multiply_dense_csr(int n, double **A, CSRMatrix *B, double **C) {
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            C[i][j] = 0.0;
        }
    }

    for (int i = 0; i < n; i++) {
        for (int k = 0; k < n; k++) {
            double a_ik = A[i][k];
            if (a_ik != 0.0) {
                int row_start = B->row_ptr[k];
                int row_end = B->row_ptr[k + 1];
                for (int idx = row_start; idx < row_end; idx++) {
                    int j = B->col_indices[idx];
                    C[i][j] += a_ik * B->values[idx];
                }
            }
        }
    }
}

CSRMatrix* create_csr_from_dense(int n, double **dense_matrix, double sparsity_threshold) {
    CSRMatrix *csr = (CSRMatrix *)malloc(sizeof(CSRMatrix));
    csr->rows = n;
    csr->cols = n;

    int nnz = 0;
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            if (dense_matrix[i][j] != 0.0) {
                nnz++;
            }
        }
    }
    csr->non_zeros = nnz;

    csr->values = (double *)malloc(nnz * sizeof(double));
    csr->col_indices = (int *)malloc(nnz * sizeof(int));
    csr->row_ptr = (int *)malloc((n + 1) * sizeof(int));

    int current_nnz = 0;
    csr->row_ptr[0] = 0;

    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            if (dense_matrix[i][j] != 0.0) {
                csr->values[current_nnz] = dense_matrix[i][j];
                csr->col_indices[current_nnz] = j;
                current_nnz++;
            }
        }
        csr->row_ptr[i + 1] = current_nnz;
    }

    return csr;
}

void free_csr(CSRMatrix *csr) {
    free(csr->values);
    free(csr->col_indices);
    free(csr->row_ptr);
    free(csr);
}

double** allocate_matrix(int n) {
    double **matrix = (double **)malloc(n * sizeof(double *));
    for (int i = 0; i < n; i++) {
        matrix[i] = (double *)malloc(n * sizeof(double));
    }
    return matrix;
}

void free_matrix(int n, double **matrix) {
    for (int i = 0; i < n; i++) {
        free(matrix[i]);
    }
    free(matrix);
}

int main(int argc, char *argv[]) {
    int n = (argc > 1) ? atoi(argv[1]) : 500;

    double **A = allocate_matrix(n);
    double **B_dense = allocate_matrix(n);
    double **C = allocate_matrix(n);

    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            A[i][j] = (i + j) % 5 == 0 ? (i + j) % 10 + 1.0 : 0.0;
            B_dense[i][j] = (i * j) % 7 == 0 ? (i - j) % 10 + 1.0 : 0.0;
            C[i][j] = 0.0;
        }
    }

    CSRMatrix *B_csr = create_csr_from_dense(n, B_dense, 0.0);

    struct timespec start, end;
    clock_gettime(CLOCK_MONOTONIC, &start);

    multiply_dense_csr(n, A, B_csr, C);

    clock_gettime(CLOCK_MONOTONIC, &end);

    double elapsed = (end.tv_sec - start.tv_sec) + (end.tv_nsec - start.tv_nsec) / 1e9;

    printf("SPARSE MULT (CSR): n = %d | Non-zeros in B = %d | Time = %.6f seconds\n", 
           n, B_csr->non_zeros, elapsed);

    free_matrix(n, A);
    free_matrix(n, B_dense);
    free_matrix(n, C);
    free_csr(B_csr);

    return 0;
}