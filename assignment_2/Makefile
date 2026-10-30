CC = gcc
CFLAGS = -O3 -std=c11 -Wall -Wextra -ffp-contract=off
LDFLAGS = -lpsapi

TARGETS = baseline.exe optimized_loop.exe optimized_tile.exe sparse_mult.exe test.exe

.PHONY: all check clean

all: $(TARGETS)

%.exe: src/%.c src/common.h
	$(CC) $(CFLAGS) $< -o $@ $(LDFLAGS)

check: test.exe
	test.exe

clean:
	del /f baseline.exe optimized_loop.exe optimized_tile.exe sparse_mult.exe test.exe