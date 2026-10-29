#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <math.h>
#include <stdint.h>
#include <windows.h>
#include <psapi.h>

static uint32_t xorshift_state = 42;

void seed_xorshift32(uint32_t seed) {
    xorshift_state = seed ? seed : 42;
}

uint32_t xorshift32() {
    uint32_t x = xorshift_state;
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    return xorshift_state = x;
}

double random_double() {
    return (double)xorshift32() / 4294967296.0;
}
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
        matrix[i] = (double *)malloc(n * sizeof(double));
        if (!matrix[i]) exit(EXIT_FAILURE);
    }
    return matrix;
}

void free_matrix(int n, double **matrix) {
    for (int i = 0; i < n; i++) free(matrix[i]);
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
        for (int j = 0; j < n; j++) C[i][j] = 0.0;
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

size_t get_peak_memory_kb() {
    PROCESS_MEMORY_COUNTERS pmc;
    if (GetProcessMemoryInfo(GetCurrentProcess(), &pmc, sizeof(pmc))) {
        return pmc.PeakWorkingSetSize / 1024;
    }
    return 0;
}

int main(int argc, char *argv[]) {
    if (argc < 2) {
        fprintf(stderr, "Usage: %s <matrix_size> [sparsity_threshold_0_to_1]\n", argv[0]);
        return EXIT_FAILURE;
    }

    int n = atoi(argv[1]);
    double sparsity_target = (argc > 2) ? atof(argv[2]) : 0.8;

    double **A = allocate_matrix(n);
    double **B_dense = allocate_matrix(n);
    double **C = allocate_matrix(n);

    seed_xorshift32(42);
    int nnz_a = 0, nnz_b = 0;

    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            double val_a = floor(random_double() * 10.0) + 1.0;
            A[i][j] = val_a;
            if (A[i][j] != 0.0) nnz_a++;

            double val_b = floor(random_double() * 10.0) + 1.0;
            double prob = random_double();
            B_dense[i][j] = (prob >= sparsity_target) ? val_b : 0.0;
            if (B_dense[i][j] != 0.0) nnz_b++;

            C[i][j] = 0.0;
        }
    }

    struct timespec conv_start, conv_end;
    clock_gettime(CLOCK_MONOTONIC, &conv_start);
    CSRMatrix *B_csr = create_csr_from_dense(n, B_dense);
    clock_gettime(CLOCK_MONOTONIC, &conv_end);
    double conversion_time = (conv_end.tv_sec - conv_start.tv_sec) + (conv_end.tv_nsec - conv_start.tv_nsec) / 1e9;

    multiply_dense_csr(n, A, B_csr, C);

    struct timespec start, end;
    clock_gettime(CLOCK_MONOTONIC, &start);
    multiply_dense_csr(n, A, B_csr, C);
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

    printf("SPARSE CSR: n = %d | TargetSparsity = %.2f | NNZ(A) = %d | NNZ(B) = %d | NNZ(C) = %d | ConvTime = %.6f seconds | MultTime = %.6f seconds | PeakMemory = %zu KB | Checksum = %.4f\n", 
                n, sparsity_target, nnz_a, nnz_b, nnz_c, conversion_time, elapsed, peak_mem_kb, checksum);

    free_matrix(n, A);
    free_matrix(n, B_dense);
    free_matrix(n, C);
    free_csr(B_csr);

    return 0;
}