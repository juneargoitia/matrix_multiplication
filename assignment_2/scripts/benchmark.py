import subprocess
import re
import os
import numpy as np
import matplotlib.pyplot as plt

os.chdir(os.path.dirname(os.path.abspath(__file__)) + "/..")

sizes = [200, 400, 600, 800, 1000, 1200, 1500]
repetitions = 7
sparsity_levels = [0.5, 0.8, 0.95]
tile_block_sizes = [16, 32, 64, 128]

executables = {
    'Baseline (Dense p=0.0)': './baseline.exe',
    'Loop Reordering (Dense p=0.0)': './optimized_loop.exe'
}

for b in tile_block_sizes:
    executables[f'Cache Tiling (B={b}, p=0.0)'] = './optimized_tile.exe'

for p in sparsity_levels:
    executables[f'Loop Reordering (p={p})'] = './optimized_loop.exe'
    executables[f'Sparse CSR (p={p})'] = './sparse_mult.exe'

os.makedirs('results', exist_ok=True)
raw_records = []
summary_data = {name: {'sizes': [], 'median': [], 'q25': [], 'q75': []} for name in executables}

print("Starting performance tests (benchmarks)...")

reference_checksums = {}

for name, exe in executables.items():
    if not os.path.exists(exe):
        print(f"  [Warning] Not found {exe}. Compile it before running the script.")
        continue

    print(f"\n Running {name}...")
    
    for n in sizes:
        times = []
        conv_times = []
        nnz_a_val = 0
        nnz_b_val = 0
        nnz_c_val = 0
        peak_mem_val = 0
        has_timeout = False
        
        for rep in range(repetitions):
            args = [exe, str(n)]
            if 'Cache Tiling' in name:
                b_val = name.split('B=')[1].split(',')[0].replace(')', '')
                args.append(b_val)
            elif 'p=' in name:
                p_val = name.split('p=')[1].replace(')', '')
                args.append(p_val)
            is_warmup = "Yes" if rep == 0 else "No"
            
            try:
                result = subprocess.run(args, capture_output=True, text=True, check=True, timeout=20)
                output = result.stdout
                
                match_mult = re.search(r'(?:MultTime|Time)\s*=\s*([0-9.]+)\s*(?:seconds?|s)?', output)
                match_conv = re.search(r'ConvTime\s*=\s*([0-9.]+)\s*(?:seconds?|s)?', output)
                match_nnz_a = re.search(r'NNZ\(A\)\s*=\s*([0-9]+)', output)
                match_nnz_b = re.search(r'NNZ\(B\)\s*=\s*([0-9]+)', output)
                match_nnz_c = re.search(r'NNZ\(C\)\s*=\s*([0-9]+)', output)
                match_mem = re.search(r'PeakMemory\s*=\s*([0-9]+)\s*KB', output)
                match_chk = re.search(r'Checksum\s*=\s*([0-9.]+)', output)
                
                if 'Sparse CSR' in name:
                    specific_mult = re.search(r'MultTime\s*=\s*([0-9.]+)\s*(?:seconds?|s)?', output)
                    t = float(specific_mult.group(1)) if specific_mult else (float(match_mult.group(1)) if match_mult else None)
                else:
                    t = float(match_mult.group(1)) if match_mult else None

                if t is not None:
                    times.append(t)
                    ct = float(match_conv.group(1)) if match_conv else 0.0
                    conv_times.append(ct)
                    
                    if match_nnz_a: nnz_a_val = int(match_nnz_a.group(1))
                    if match_nnz_b: nnz_b_val = int(match_nnz_b.group(1))
                    if match_nnz_c: nnz_c_val = int(match_nnz_c.group(1))
                    if match_mem: peak_mem_val = int(match_mem.group(1))
                    
                    chk_val = float(match_chk.group(1)) if match_chk else 0.0
                    
                    key_chk = (n, 'p=0.0' if 'p=0.0' in name or 'Dense' in name else name.split('p=')[1])
                    if key_chk not in reference_checksums:
                        reference_checksums[key_chk] = chk_val
                    else:
                        if abs(reference_checksums[key_chk] - chk_val) > 1e-4:
                            print(f"    [Alert Checksum] Discrepance in n={n} for {name}: {chk_val} vs ref {reference_checksums[key_chk]}")
                    
                    raw_records.append(f"{n},{name},{rep},{is_warmup},{t:.6f},{ct:.6f},{nnz_a_val},{nnz_b_val},{nnz_c_val},{peak_mem_val},OK\n")
                else:
                    raw_records.append(f"{n},{name},{rep},{is_warmup},NaN,NaN,0,0,0,0,PARSE_ERROR\n")
            
            except subprocess.TimeoutExpired:
                has_timeout = True
                raw_records.append(f"{n},{name},{rep},{is_warmup},NaN,NaN,0,0,0,0,TIMEOUT\n")
                print(f"    [Timeout Registered] n={n}, rep={rep}: Time limit exceeded (20s).")
            except Exception as e:
                raw_records.append(f"{n},{name},{rep},{is_warmup},NaN,NaN,0,0,0,0,ERROR\n")
                print(f"    [Error] n={n}, rep={rep}: {e}")
        
        valid_times = times[1:] if (len(times) > 1 and not has_timeout) else []
        
        if valid_times:
            med = float(np.median(valid_times))
            q25 = float(np.percentile(valid_times, 25))
            q75 = float(np.percentile(valid_times, 75))
            
            summary_data[name]['sizes'].append(n)
            summary_data[name]['median'].append(med)
            summary_data[name]['q25'].append(q25)
            summary_data[name]['q75'].append(q75)
            print(f"  n = {n:4d} | Mult Median = {med:.6f} s | IQR = {q75 - q25:.6f} s | Peak RAM = {peak_mem_val} KB")
        else:
            print(f"  n = {n:4d} | Omitted from summary due to timeout or insufficient data.")
            
raw_csv_path = 'results/raw_data_detailed.csv'
with open(raw_csv_path, 'w', encoding='utf-8') as f:
    f.write("Size,Method,Repetition,IsWarmup,TimeSeconds,ConvTimeSeconds,NNZ_A,NNZ_B,NNZ_C,PeakMemoryKB,Status\n")
    f.writelines(raw_records)
print(f"\n Results saved successfully in '{raw_csv_path}'")

plt.figure(figsize=(12, 7))
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
plt.title('Comparative Performance (Median and Interquartile Range)', fontsize=14, fontweight='bold')
plt.legend(fontsize=8, loc='upper left')
plt.grid(True, linestyle='--', alpha=0.7)

plot_path = 'results/performance_plot_robust.png'
plt.savefig(plot_path, dpi=300, bbox_inches='tight')
print(f"Graph saved in '{plot_path}'")

plt.close()