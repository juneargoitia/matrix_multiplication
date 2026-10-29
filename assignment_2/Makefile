CC = gcc
CFLAGS = -O3 -std=c11 -Wall -Wextra

SRC_DIR = src
BIN_DIR = .

.PHONY: all clean

all: baseline optimized_loop optimized_tile sparse_mult

baseline: $(SRC_DIR)/baseline.c
	$(CC) $(CFLAGS) $(SRC_DIR)/baseline.c -o $(BIN_DIR)/baseline.exe

optimized_loop: $(SRC_DIR)/optimized_loop.c
	$(CC) $(CFLAGS) $(SRC_DIR)/optimized_loop.c -o $(BIN_DIR)/optimized_loop.exe

optimized_tile: $(SRC_DIR)/optimized_tile.c
	$(CC) $(CFLAGS) $(SRC_DIR)/optimized_tile.c -o $(BIN_DIR)/optimized_tile.exe

sparse_mult: $(SRC_DIR)/sparse_mult.c
	$(CC) $(CFLAGS) $(SRC_DIR)/sparse_mult.c -o $(BIN_DIR)/sparse_mult.exe

test: $(SRC_DIR)/test.c
	$(CC) $(CFLAGS) $(SRC_DIR)/test.c -o $(BIN_DIR)/test.exe
	
clean:
	@if exist *.exe del /f /q *.exe