CC = gcc
CFLAGS = -O3 -std=c11 -Wall -Wextra -ffp-contract=off
LDFLAGS = -lpsapi

TARGETS = run_matmul_seq.exe run_matmul_omp.exe test.exe

.PHONY: all check clean

all: $(TARGETS)

run_matmul_seq.exe: src/run_matmul.c src/common.h
	$(CC) $(CFLAGS) $< -o $@ $(LDFLAGS)

run_matmul_omp.exe: src/run_matmul.c src/common.h
	$(CC) $(CFLAGS) -fopenmp $< -o $@ $(LDFLAGS)

test.exe: src/test.c src/common.h
	$(CC) $(CFLAGS) -fopenmp $< -o $@ $(LDFLAGS)

check: test.exe
	test.exe

clean:
	del /f run_matmul_seq.exe run_matmul_omp.exe test.exe