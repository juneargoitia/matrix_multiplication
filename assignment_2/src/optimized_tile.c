#include <stdio.h>
#include <stdlib.h>
#include <time.h>


void multiply_optimized_tile(int n, double **A, double **B, double **C, int block_size) {
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            C[i][j] = 0.0;
        }
    }

    for (int sj = 0; sj < n; sj += block_size) {
        for (int sk = 0; sk < n; sk += block_size) {
            for (int si = 0; si < n; si += block_size) {
                
                int imax = (si + block_size < n) ? si + block_size : n;
                int kmax = (sk + block_size < n) ? sk + block_size : n;
                int jmax = (sj + block_size < n) ? sj + block_size : n;

                for (int i = si; i < imax; i++) {
                    for (int k = sk; k < kmax; k++) {
                        double r = A[i][k];
                        for (int j = sj; j < jmax; j++) {
                            C[i][j] += r * B[k][j];
                        }
                    }
                }

            }
        }
    }
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
    int block_size = (argc > 2) ? atoi(argv[2]) : 64;
    
    double **A = allocate_matrix(n);
    double **B = allocate_matrix(n);
    double **C = allocate_matrix(n);

    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            A[i][j] = (i + j) % 10 + 1.0;
            B[i][j] = (i - j) % 10 + 1.0;
            C[i][j] = 0.0;
        }
    }

    struct timespec start, end;
    clock_gettime(CLOCK_MONOTONIC, &start);

    multiply_optimized_tile(n, A, B, C, block_size);

    clock_gettime(CLOCK_MONOTONIC, &end);

    double elapsed = (end.tv_sec - start.tv_sec) + (end.tv_nsec - start.tv_nsec) / 1e9;

    double checksum = 0.0;
    for (int i = 0; i < n; i++) checksum += C[i][i];

    printf("OPTIMIZED (Cache Tiling): n = %d | Block Size = %d | Checksum = %.4f | Time = %.6f seconds\n", n, block_size, checksum, elapsed);

    free_matrix(n, A);
    free_matrix(n, B);
    free_matrix(n, C);

    return 0;
}