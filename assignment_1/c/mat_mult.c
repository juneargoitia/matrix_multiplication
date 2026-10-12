#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>

#ifdef _WIN32
#include <windows.h>
static double now_seconds(void) {
    LARGE_INTEGER freq, cnt;
    QueryPerformanceFrequency(&freq);
    QueryPerformanceCounter(&cnt);
    return (double)cnt.QuadPart / (double)freq.QuadPart;
}
#else
#include <time.h>
static double now_seconds(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec + (double)ts.tv_nsec * 1e-9;
}
#endif

#if defined(__GNUC__) || defined(__clang__)
#define NOINLINE __attribute__((noinline))
#else
#define NOINLINE
#endif

static NOINLINE void matmul(const double *restrict a, const double *restrict b,
                            double *restrict c, size_t n) {
    for (size_t i = 0; i < n; i++) {
        for (size_t j = 0; j < n; j++) {
            double sum = 0.0;
            for (size_t k = 0; k < n; k++) {
                sum += a[i * n + k] * b[k * n + j];
            }
            c[i * n + j] = sum;
        }
    }
}

static int read_matrix(const char *path, double *buf, size_t count) {
    FILE *f = fopen(path, "rb");
    if (!f) {
        perror(path);
        return 0;
    }
    size_t got = fread(buf, sizeof(double), count, f);
    int extra = (fgetc(f) != EOF);
    fclose(f);
    if (got != count || extra) {
        fprintf(stderr, "%s: expected exactly %zu doubles\n", path, count);
        return 0;
    }
    return 1;
}

static int write_matrix(const char *path, const double *buf, size_t count) {
    FILE *f = fopen(path, "wb");
    if (!f) {
        perror(path);
        return 0;
    }
    size_t put = fwrite(buf, sizeof(double), count, f);
    fclose(f);
    return put == count;
}

int main(int argc, char **argv) {
    if (argc != 6 && argc != 7) {
        fprintf(stderr, "usage: %s A.bin B.bin n warmup reps [out.bin]\n", argv[0]);
        return 2;
    }
    char *end = NULL;
    unsigned long long n_ull = strtoull(argv[3], &end, 10);
    if (*end != '\0' || n_ull == 0) {
        fprintf(stderr, "invalid n\n");
        return 2;
    }
    long warmup = strtol(argv[4], &end, 10);
    if (*end != '\0' || warmup < 0) {
        fprintf(stderr, "invalid warmup\n");
        return 2;
    }
    long reps = strtol(argv[5], &end, 10);
    if (*end != '\0' || reps < 1) {
        fprintf(stderr, "invalid reps\n");
        return 2;
    }
    size_t n = (size_t)n_ull;
    if (n > SIZE_MAX / n) {
        fprintf(stderr, "n too large\n");
        return 2;
    }
    size_t count = n * n;

    double *a = (double *)malloc(count * sizeof(double));
    double *b = (double *)malloc(count * sizeof(double));
    double *c = (double *)calloc(count, sizeof(double));
    if (!a || !b || !c) {
        fprintf(stderr, "allocation failed (out of memory) for n=%zu\n", n);
        return 3;
    }
    if (!read_matrix(argv[1], a, count) || !read_matrix(argv[2], b, count)) return 4;

#ifdef __VERSION__
    printf("INFO,compiler,%s\n", __VERSION__);
#endif
    printf("INFO,lang,c\nINFO,n,%zu\n", n);
    fflush(stdout);

    for (long w = 0; w < warmup; w++) {
        double t0 = now_seconds();
        matmul(a, b, c, n);
        double t1 = now_seconds();
        printf("WARMUP,%ld,%.9f\n", w, t1 - t0);
        fflush(stdout);
    }
    for (long r = 0; r < reps; r++) {
        double t0 = now_seconds();
        matmul(a, b, c, n);
        double t1 = now_seconds();
        printf("REP,%ld,%.9f\n", r, t1 - t0);
        fflush(stdout);
    }

    double checksum = 0.0;
    for (size_t i = 0; i < count; i++) checksum += c[i];
    printf("CHECKSUM,%.17g\n", checksum);
    fflush(stdout);

    if (argc == 7 && !write_matrix(argv[6], c, count)) return 5;

    if (getenv("MATMUL_HOLD")) {
        printf("DONE\n");
        fflush(stdout);
        while (getchar() != EOF) {}
    }

    free(a);
    free(b);
    free(c);
    return 0;
}
