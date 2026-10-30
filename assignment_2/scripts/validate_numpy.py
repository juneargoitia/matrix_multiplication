import numpy as np

def xorshift32(state):
    x = state
    x ^= (x << 13) & 0xFFFFFFFF
    x ^= (x >> 17) & 0xFFFFFFFF
    x ^= (x << 5) & 0xFFFFFFFF
    return x

def generate_matrices(n, seed=42, sparsity=0.5):
    state = seed
    A = np.zeros((n, n), dtype=np.float64)
    B = np.zeros((n, n), dtype=np.float64)
    
    def next_double():
        nonlocal state
        state = xorshift32(state)
        return float(state) / 4294967296.0

    for i in range(n):
        for j in range(n):
            val_a = np.floor(next_double() * 10.0) + 1.0
            A[i, j] = val_a
            
            val_b = np.floor(next_double() * 10.0) + 1.0
            prob_b = next_double()
            B[i, j] = val_b if prob_b >= sparsity else 0.0
            
    return A, B

if __name__ == "__main__":
    n = 65
    A, B = generate_matrices(n, seed=42, sparsity=0.5)
    C_numpy = np.dot(A, B)
    
    print(f"NumPy validation OK: Matrix {n}x{n} generated with Xorshift32.")
    print(f"Checksum NumPy (trace of C): {np.trace(C_numpy):.4f}")