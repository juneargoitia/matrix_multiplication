#include <stdio.h>
#include <stdlib.h>
#include <time.h>

double** allocate_matrix(int n) {
    double **matrix = (double **)malloc(n * sizeof(double *));
    if (matrix == NULL) {
        fprintf(stderr, "Error: Failed to allocate memory for the rows.\n");
        exit(EXIT_FAILURE);
    }
    for (int i = 0; i < n; i++) {
        matrix[i] = (double *)malloc(n * sizeof(double));
        if (matrix[i] == NULL) {
            fprintf(stderr, "Error: Failed to allocate memory for the columns.\n");
            exit(EXIT_FAILURE);
        }
    }
    return matrix;
}

void free_matrix(int n, double **matrix) {
    for (int i = 0; i < n; i++) {
        free(matrix[i]);
    }
    free(matrix);
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

int main(int argc, char *argv[]) {
    if (argc < 2) {
        fprintf(stderr, "Usage: %s <matrix_size>\n", argv[0]);
        return EXIT_FAILURE;
    }

    int n = atoi(argv[1]);
    if (n <= 0) {
        fprintf(stderr, "Error: The matrix size must be greater than 0.\n");
        return EXIT_FAILURE;
    }
    
    double **A = allocate_matrix(n);
    double **B = allocate_matrix(n);
    double **C = allocate_matrix(n);

    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            A[i][j] = (double)((i + j) % 10 + 1.0);
            B[i][j] = (double)((i - j) % 10 + 1.0);
            C[i][j] = 0.0;
        }
    }

    struct timespec start, end;
    clock_gettime(CLOCK_MONOTONIC, &start);

    multiply_baseline(n, A, B, C);

    clock_gettime(CLOCK_MONOTONIC, &end);

    double elapsed = (end.tv_sec - start.tv_sec) + (end.tv_nsec - start.tv_nsec) / 1e9;

    double checksum = 0.0;
    for (int i = 0; i < n; i++) {
        checksum += C[i][i];
    }

    printf("BASELINE (Naive): n = %d | Checksum = %.4f | Time = %.6f seconds\n", n, checksum, elapsed);
    
    free_matrix(n, A);
    free_matrix(n, B);
    free_matrix(n, C);

    return 0;
}