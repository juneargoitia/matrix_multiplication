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

void multiply_loop(int n, double **A, double **B, double **C) {
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            C[i][j] = 0.0;
        }
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
    for (int i = 0; i < n; i++) {
        free(matrix[i]);
    }
    free(matrix);
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
        fprintf(stderr, "Uso: %s <matrix_size>\n", argv[0]);
        return EXIT_FAILURE;
    }

    int n = atoi(argv[1]);
    double **A = allocate_matrix(n);
    double **B = allocate_matrix(n);
    double **C = allocate_matrix(n);

    seed_xorshift32(42);
    int nnz_a = 0, nnz_b = 0;
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            A[i][j] = floor(random_double() * 10.0) + 1.0;
            B[i][j] = floor(random_double() * 10.0) + 1.0;
            if (A[i][j] != 0.0) nnz_a++;
            if (B[i][j] != 0.0) nnz_b++;
            C[i][j] = 0.0;
        }
    }

    multiply_loop(n, A, B, C);

    struct timespec start, end;
    clock_gettime(CLOCK_MONOTONIC, &start);

    multiply_loop(n, A, B, C);

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

    printf("LOOP REORDERING: n = %d | NNZ(A) = %d | NNZ(B) = %d | NNZ(C) = %d | Time = %.6f seconds | PeakMemory = %zu KB | Checksum = %.4f\n",
            n, nnz_a, nnz_b, nnz_c, elapsed, peak_mem_kb, checksum);

    free_matrix(n, A);
    free_matrix(n, B);
    free_matrix(n, C);

    return 0;
}