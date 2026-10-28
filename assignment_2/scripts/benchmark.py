import subprocess
import re
import os
import numpy as np
import matplotlib.pyplot as plt

sizes = [200, 400, 600, 800, 1000]
repetitions = 7
sparsity_level = 0.8

executables = {
    'Baseline (Naive)': './baseline.exe',
    'Loop Reordering': './optimized_loop.exe',
    'Cache Tiling (B=64)': './optimized_tile.exe',
    'Sparse CSR': './sparse_mult.exe'
}

os.makedirs('results', exist_ok=True)
raw_records = []
summary_data = {name: {'sizes': [], 'median': [], 'iqr': []} for name in executables}

print("Starting performance tests (benchmarks)...")

for name, exe in executables.items():
    if not os.path.exists(exe):
        print(f"  [Warning] Not found {exe}. Compile it before running the script.")
        continue
    print(f"\n Running {name}...")
    
    for n in sizes:
        times = []
        for rep in range(repetitions):
            args = [exe, str(n)]
            if 'Cache Tiling' in name:
                args.append('64')
            elif 'Sparse CSR' in name:
                args.append(str(sparsity_level))
            
            try:
                result = subprocess.run(args, capture_output=True, text=True, check=True)
                match = re.search(r'(?:Time|MultTime)\s*=\s*([0-9.]+)\s*seconds', result.stdout)
                if match:
                    t = float(match.group(1))
                    times.append(t)
                    is_warmup = "Yes" if rep == 0 else "No"
                    raw_records.append(f"{n},{name},{rep},{is_warmup},{t}\n")
            except Exception as e:
                print(f" [Error] n={n}, rep={rep}: {e}")
        
        valid_times = times[1:] if len(times) > 1 else times
        if valid_times:
            med = np.median(valid_times)
            q75, q25 = np.percentile(valid_times, [75 ,25])
            iqr = q75 - q25
            
            summary_data[name]['sizes'].append(n)
            summary_data[name]['median'].append(med)
            summary_data[name]['iqr'].append(iqr)
            print(f" n={n:4d} | Median: {med:.6f} s | IQR: {iqr:.6f} s")
            
raw_csv_path = 'results/benchmark_results.csv'
with open(raw_csv_path, 'w', encoding='utf-8') as f:
    f.write("Size,Method,Repetition,IsWarmup,TimeSeconds\n")
    f.writelines(raw_records)
print(f"\n Results saved successfully in '{raw_csv_path}'")

plt.figure(figsize=(10, 6))
for name, dat in summary_data.items():
        if dat['sizes']:
            plt.errorbar(
                dat['sizes'],
                dat['median'],
                yerr=dat['iqr'],
                marker='o', linewidth=2, capsize=4,
                label=name
            )
            
plt.xlabel('Matrix size (n)', fontsize=12)
plt.ylabel('Execution Time - Median (seconds)', fontsize=12)
plt.title('Performance with Statistical Rigor (Median and IQR)', fontsize=14, fontweight='bold')
plt.legend(fontsize=10)
plt.grid(True, linestyle='--', alpha=0.7)

plot_path = 'results/performance_plot.png'
plt.savefig(plot_path, dpi=300, bbox_inches='tight')
print(f"Graph successfully generated and saved in '{plot_path}'")

plt.close()