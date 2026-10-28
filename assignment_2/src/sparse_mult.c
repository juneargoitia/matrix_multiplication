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

double** allocate_matrix(int n) {
    double **matrix = (double **)malloc(n * sizeof(double *));
    if (!matrix) { exit(EXIT_FAILURE); }
    for (int i = 0; i < n; i++) {
        matrix[i] = (double *)malloc(n * sizeof(double));
        if (!matrix[i]) { exit(EXIT_FAILURE); }
    }
    return matrix;
}

void free_matrix(int n, double **matrix) {
    for (int i = 0; i < n; i++) {
        free(matrix[i]);
    }
    free(matrix);
}

CSRMatrix* create_csr_from_dense(int n, double **dense_matrix) {
    CSRMatrix *csr = (CSRMatrix *)malloc(sizeof(CSRMatrix));
    csr->rows = n;
    csr->cols = n;

    int nnz = 0;
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            if (dense_matrix[i][j] != 0.0) nnz++;
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

int main(int argc, char *argv[]) {
    if (argc < 2) {
        fprintf(stderr, "Usage: %s <matrix_size>\n", argv[0]);
        return EXIT_FAILURE;
    }

    int n = atoi(argv[1]);
    double sparsity_target = (argc > 2) ? atof(argv[2]) : 0.8;

    double **A = allocate_matrix(n);
    double **B_dense = allocate_matrix(n);
    double **C = allocate_matrix(n);

    srand(42);
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            A[i][j] = ((double)rand() / RAND_MAX < 0.5) ? ((double)(rand() % 10) + 1.0) : 0.0;
            
            double prob = (double)rand() / RAND_MAX;
            B_dense[i][j] = (prob >= sparsity_target) ? ((double)(rand() % 10) + 1.0) : 0.0;
            C[i][j] = 0.0;
        }
    }

    struct timespec conv_start, conv_end;
    clock_gettime(CLOCK_MONOTONIC, &conv_start);
    CSRMatrix *B_csr = create_csr_from_dense(n, B_dense);
    clock_gettime(CLOCK_MONOTONIC, &conv_end);
    double conversion_time = (conv_end.tv_sec - conv_start.tv_sec) + (conv_end.tv_nsec - conv_start.tv_nsec) / 1e9;

    struct timespec start, end;
    clock_gettime(CLOCK_MONOTONIC, &start);
    multiply_dense_csr(n, A, B_csr, C);
    clock_gettime(CLOCK_MONOTONIC, &end);
    double elapsed = (end.tv_sec - start.tv_sec) + (end.tv_nsec - start.tv_nsec) / 1e9;

    double checksum = 0.0;
    for (int i = 0; i < n; i++) checksum += C[i][i];

    printf("SPARSE CSR: n = %d | NNZ(B) = %d | ConvTime = %.6fs | MultTime = %.6fs | Checksum = %.4f\n", 
           n, B_csr->non_zeros, conversion_time, elapsed, checksum);

    free_matrix(n, A);
    free_matrix(n, B_dense);
    free_matrix(n, C);
    free_csr(B_csr);

    return 0;
}