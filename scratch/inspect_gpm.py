from pathlib import Path
import h5py

# Deep inspect the HDF5 file to find the FileHeader
hf_file = list(Path("data/rainfall/raw").glob("*.HDF5"))[0]
print(f"File: {hf_file.name}")
with h5py.File(hf_file, "r") as hf:
    fh = hf.attrs.get("FileHeader", b"")
    if isinstance(fh, bytes):
        fh = fh.decode("utf-8", errors="replace")
    print(f"FileHeader excerpt (first 400 chars): {fh[:400]}")
    fi = hf.attrs.get("FileInfo", b"")
    if isinstance(fi, bytes):
        fi = fi.decode("utf-8", errors="replace")
    print(f"FileInfo excerpt (first 300 chars): {fi[:300]}")
    gh = hf["Grid"].attrs.get("GridHeader", b"")
    if isinstance(gh, bytes):
        gh = gh.decode("utf-8", errors="replace")
    print(f"GridHeader excerpt (first 200 chars): {gh[:200]}")
    # Show available datasets in Grid
    print(f"Grid datasets: {list(hf['Grid'].keys())[:10]}")
