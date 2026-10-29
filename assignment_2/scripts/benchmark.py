import subprocess
import re
import os
import numpy as np
import matplotlib.pyplot as plt

os.chdir(os.path.dirname(os.path.abspath(__file__)) + "/..")

sizes = [200, 400, 600, 800, 1000, 1200, 1500]
repetitions = 7
sparsity_levels = [0.5, 0.8, 0.95]

executables = {
    'Baseline (Naive)': './baseline.exe',
    'Loop Reordering': './optimized_loop.exe',
    'Cache Tiling (B=64)': './optimized_tile.exe',
}

for p in sparsity_levels:
    executables[f'Sparse CSR (p={p})'] = './sparse_mult.exe'

os.makedirs('results', exist_ok=True)
raw_records = []
summary_data = {name: {'sizes': [], 'median': [], 'q25': [], 'q75': []} for name in executables}

print("Starting performance tests (benchmarks)...")

for name, exe in executables.items():
    if not os.path.exists(exe):
        print(f"  [Warning] Not found {exe}. Compile it before running the script.")
        continue

    print(f"\n Running {name}...")
    
    for n in sizes:
        times = []
        conv_times = []
        nnz_b_val = 0
        
        for rep in range(repetitions):
            args = [exe, str(n)]
            if 'Cache Tiling' in name:
                args.append('64')
            elif 'Sparse CSR' in name:
                p_val = name.split('p=')[1].replace(')', '')
                args.append(p_val)
            
            try:
                result = subprocess.run(args, capture_output=True, text=True, check=True, timeout=20)
                output = result.stdout
                
                match = re.search(r'(?:Time|MultTime)\s*=\s*([0-9.]+)\s*(?:seconds?|s)?', output)
                match_conv = re.search(r'ConvTime\s*=\s*([0-9.]+)\s*(?:seconds?|s)?', output)
                match_nnz = re.search(r'NNZ\(B\)\s*=\s*([0-9]+)', output)
                
                if match:
                    t = float(match.group(1))
                    times.append(t)
                    
                    ct = float(match_conv.group(1)) if match_conv else 0.0
                    conv_times.append(ct)
                    
                    if match_nnz:
                        nnz_b_val = int(match_nnz.group(1))
                    
                    is_warmup = "Yes" if rep == 0 else "No"
                    raw_records.append(f"{n},{name},{rep},{is_warmup},{t:.6f},{ct:.6f},{nnz_b_val}\n")
            except subprocess.TimeoutExpired:
                print(f"    [Timeout] n={n}, rep={rep}: Time limit exceeded (20s).")
                        
            except Exception as e:
                print(f" [Error] n={n}, rep={rep}: {e}")
        
        valid_times = times[1:] if len(times) > 1 else times
        
        if valid_times:
            med = float(np.median(valid_times))
            q25 = float(np.percentile(valid_times, 25))
            q75 = float(np.percentile(valid_times, 75))
            
            summary_data[name]['sizes'].append(n)
            summary_data[name]['median'].append(med)
            summary_data[name]['q25'].append(q25)
            summary_data[name]['q75'].append(q75)
            print(f" n={n:4d} | Median: {med:.6f} s | IQR = {q75 - q25:.6f} s")
            
raw_csv_path = 'results/raw_data_detailed.csv'
with open(raw_csv_path, 'w', encoding='utf-8') as f:
    f.write("Size,Method,Repetition,IsWarmup,TimeSeconds,ConvTimeSeconds,NNZ_B\n")
    f.writelines(raw_records)
print(f"\n Results saved successfully in '{raw_csv_path}'")

plt.figure(figsize=(10, 6))
for name, dat in summary_data.items():
        if dat['sizes']:
            meds = np.array(dat['median'])
            q25s = np.array(dat['q25'])
            q75s = np.array(dat['q75'])
            y_errs = [meds - q25s, q75s - meds]
        
            plt.errorbar(
                dat['sizes'], meds,
                yerr=y_errs,
                marker='o', linewidth=2, capsize=4,
                label=name
            )
            
plt.xlabel('Matrix size (n)', fontsize=12)
plt.ylabel('Execution Time - Median (seconds)', fontsize=12)
plt.title('Performance with Statistical Rigor (Median and IQR)', fontsize=14, fontweight='bold')
plt.legend(fontsize=9, loc='upper left')
plt.grid(True, linestyle='--', alpha=0.7)

plot_path = 'results/performance_plot_robust.png'
plt.savefig(plot_path, dpi=300, bbox_inches='tight')
print(f"Graph successfully generated and saved in '{plot_path}'")

plt.close()