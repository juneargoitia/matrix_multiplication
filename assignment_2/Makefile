CC = gcc
CFLAGS = -O3 -Wall -Wextra

all: baseline optimized_loop

baseline: src/baseline.c
	$(CC) $(CFLAGS) src/baseline.c -o baseline

optimized_loop: src/optimized_loop.c
	$(CC) $(CFLAGS) src/optimized_loop.c -o optimized_loop

clean:
	rm -f baseline optimized_loop