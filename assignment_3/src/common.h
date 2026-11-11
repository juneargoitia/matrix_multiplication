#ifndef COMMON_H
#define COMMON_H

#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <math.h>
#include <stdint.h>
#include <windows.h>
#include <psapi.h>

#ifdef _OPENMP
#include <omp.h>
#endif

static uint32_t xorshift_state = 42;

static inline void seed_xorshift32(uint32_t seed) {
    xorshift_state = seed ? seed : 42;
}

static inline uint32_t xorshift32(void) {
    uint32_t x = xorshift_state;
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    return xorshift_state = x;
}

static inline double random_double(void) {
    return (double)xorshift32() / 4294967296.0;
}

static inline double** allocate_matrix(int n) {
    double **matrix = (double **)malloc(n * sizeof(double *));
    if (!matrix) exit(EXIT_FAILURE);
    for (int i = 0; i < n; i++) {
        matrix[i] = (double *)malloc(n * sizeof(double));
        if (!matrix[i]) exit(EXIT_FAILURE);
    }
    return matrix;
}

static inline void free_matrix(int n, double **matrix) {
    for (int i = 0; i < n; i++) free(matrix[i]);
    free(matrix);
}

static inline size_t get_peak_memory_kb(void) {
    PROCESS_MEMORY_COUNTERS pmc;
    if (GetProcessMemoryInfo(GetCurrentProcess(), &pmc, sizeof(pmc))) {
        return pmc.PeakWorkingSetSize / 1024;
    }
    return 0;
}

static inline void generate_matrices(int n, double p, double **A, double **B, double **C,
                                     int *nnz_a, int *nnz_b) {
    seed_xorshift32(42);
    int na = 0, nb = 0;
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            double val_a = floor(random_double() * 10.0) + 1.0;
            double val_b = floor(random_double() * 10.0) + 1.0;
            double prob_b = random_double();
            A[i][j] = val_a;
            B[i][j] = (prob_b >= p) ? val_b : 0.0;
            if (A[i][j] != 0.0) na++;
            if (B[i][j] != 0.0) nb++;
            if (C) C[i][j] = 0.0;
        }
    }
    if (nnz_a) *nnz_a = na;
    if (nnz_b) *nnz_b = nb;
}

static inline void multiply_loop_parallel(int n, double **A, double **B, double **C, int threads) {
#ifdef _OPENMP
    if (threads > 0) {
        omp_set_num_threads(threads);
    }
    #pragma omp parallel
    {
        #pragma omp for schedule(static)
        for (int i = 0; i < n; i++) {
            for (int j = 0; j < n; j++) {
                C[i][j] = 0.0;
            }
        }

        #pragma omp for schedule(static)
        for (int i = 0; i < n; i++) {
            for (int k = 0; k < n; k++) {
                double a_ik = A[i][k];
                if (a_ik != 0.0) {
                    for (int j = 0; j < n; j++) {
                        C[i][j] += a_ik * B[k][j];
                    }
                }
            }
        }
    }
#else
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) C[i][j] = 0.0;
    }
    for (int i = 0; i < n; i++) {
        for (int k = 0; k < n; k++) {
            double a_ik = A[i][k];
            if (a_ik != 0.0) {
                for (int j = 0; j < n; j++) {
                    C[i][j] += a_ik * B[k][j];
                }
            }
        }
    }
#endif
}

static inline void multiply_tile_parallel(int n, double **A, double **B, double **C, int block_size, int threads) {
#ifdef _OPENMP
    if (threads > 0) {
        omp_set_num_threads(threads);
    }
    #pragma omp parallel
    {
        #pragma omp for schedule(static)
        for (int i = 0; i < n; i++) {
            for (int j = 0; j < n; j++) {
                C[i][j] = 0.0;
            }
        }


        #pragma omp for schedule(static)
        for (int ii = 0; ii < n; ii += block_size) {
            for (int kk = 0; kk < n; kk += block_size) {
                for (int jj = 0; jj < n; jj += block_size) {
                    int i_max = (ii + block_size < n) ? ii + block_size : n;
                    int k_max = (kk + block_size < n) ? kk + block_size : n;
                    int j_max = (jj + block_size < n) ? jj + block_size : n;

                    for (int i = ii; i < i_max; i++) {
                        for (int k = kk; k < k_max; k++) {
                            double a_ik = A[i][k];
                            if (a_ik != 0.0) {
                                for (int j = jj; j < j_max; j++) {
                                    C[i][j] += a_ik * B[k][j];
                                }
                            }
                        }
                    }
                }
            }
        }
    }
#else
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
                        if (a_ik != 0.0) {
                            for (int j = jj; j < j_max; j++) {
                                C[i][j] += a_ik * B[k][j];
                            }
                        }
                    }
                }
            }
        }
    }
#endif
}

#endif