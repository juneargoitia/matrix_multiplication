import subprocess
import re
import os
import matplotlib.pyplot as plt

sizes = [200, 400, 600, 800, 1000]

executables = {
    'Baseline (Naive)': './baseline.exe',
    'Loop Reordering': './optimized_loop.exe',
    'Cache Tiling (B=64)': './optimized_tile.exe',
    'Sparse CSR': './sparse_mult.exe'
}

data = {name: [] for name in executables}

os.makedirs('results', exist_ok=True)

print("Starting performance tests (benchmarks)...")

for n in sizes:
    print(f" Testing matrix size n = {n}...")
    for name, exe in executables.items():
        if not os.path.exists(exe):
            print(f"  [Warning] Not found {exe}. Compile it before running the script.")
            data[name].append(None)
            continue

        args = [exe, str(n)]
        if 'Cache Tiling' in name:
            args.append('64')
            
        try:
            result = subprocess.run(args, capture_output=True, text=True, check=True)
            output = result.stdout
            
            match = re.search(r'Time\s*=\s*([0-9.]+)\s*seconds', output)
            if match:
                t = float(match.group(1))
                data[name].append(t)
            else:
                data[name].append(None)
        except Exception as e:
            print(f"  [Error] Execution failed for {exe}: {e}")
            data[name].append(None)

csv_path = 'results/benchmark_results.csv'
with open(csv_path, 'w', encoding='utf-8') as f:
    f.write("Size," + ",".join(executables.keys()) + "\n")
    for i, n in enumerate(sizes):
        row = [str(n)]
        for name in executables.keys():
            val = data[name][i] if i < len(data[name]) else None
            row.append(str(val) if val is not None else "N/A")
        f.write(",".join(row) + "\n")

print(f"\n Results saved successfully in '{csv_path}'")

plt.figure(figsize=(10, 6))
for name, times in data.items():
    valid_times = [t for t in times if t is not None]
    valid_sizes = [sizes[i] for i, t in enumerate(times) if t is not None]
    if valid_times:
        plt.plot(valid_sizes, valid_times, marker='o', linewidth=2, label=name)

plt.xlabel('Matrix size (n)', fontsize=12)
plt.ylabel('Execution Time (seconds)', fontsize=12)
plt.title('Performance Comparison - Matrix Multiplication', fontsize=14, fontweight='bold')
plt.legend(fontsize=10)
plt.grid(True, linestyle='--', alpha=0.7)

plot_path = 'results/performance_plot.png'
plt.savefig(plot_path, dpi=300, bbox_inches='tight')
print(f"Graph successfully generated and saved in '{plot_path}'")

plt.close()