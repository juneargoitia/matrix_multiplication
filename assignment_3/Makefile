CC = gcc
CFLAGS = -O3 -std=c11 -Wall -Wextra -ffp-contract=off
LDFLAGS = -lpsapi

TARGETS = run_matmul_seq.exe run_matmul_omp.exe test_seq.exe test_omp.exe

.PHONY: all check clean

all: $(TARGETS)

run_matmul_seq.exe: src/run_matmul.c src/common.h
	$(CC) $(CFLAGS) $< -o $@ $(LDFLAGS)

run_matmul_omp.exe: src/run_matmul.c src/common.h
	$(CC) $(CFLAGS) -fopenmp $< -o $@ $(LDFLAGS)

test_seq.exe: src/test.c src/common.h
	$(CC) $(CFLAGS) $< -o $@ $(LDFLAGS)

test_omp.exe: src/test.c src/common.h
	$(CC) $(CFLAGS) -fopenmp $< -o $@ $(LDFLAGS)

check: test_seq.exe test_omp.exe
	test_seq.exe
	test_omp.exe

clean:
	del /f run_matmul_seq.exe run_matmul_omp.exe test_seq.exe test_omp.exe