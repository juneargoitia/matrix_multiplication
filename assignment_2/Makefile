CC = gcc
CFLAGS = -O3 -std=c11 -Wall -Wextra -ffp-contract=off
LDFLAGS = -lpsapi

TARGETS = baseline.exe optimized_loop.exe optimized_tile.exe sparse_mult.exe test.exe

all: $(TARGETS)

%.exe: src/%.c src/common.h
	$(CC) $(CFLAGS) $< -o $@ $(LDFLAGS)

clean:
	del /f baseline.exe optimized_loop.exe optimized_tile.exe sparse_mult.exe test.exe
	if exist results\raw_data_detailed.csv del /f results\raw_data_detailed.csv