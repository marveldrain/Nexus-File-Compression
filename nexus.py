import sys
import os
import hashlib
from pathlib import Path
import time
import pickle
import lzma
from collections import defaultdict

class NexusCompressor:
    def __init__(self):
        self.context_order = 6
        self.max_match = 256
        self.context_table = defaultdict(lambda: defaultdict(int))
    
    def update_context(self, context: tuple, byte: int):
        self.context_table[context][byte] += 1
    
    def predict_byte(self, context: tuple) -> int:
        counts = self.context_table[context]
        if not counts:
            return 0
        return max(counts, key=counts.get)
    
    def compress(self, data: bytes) -> bytes:
        start = time.time()
        original_size = len(data)
        
        compressed = bytearray()
        i = 0
        while i < len(data):
            # Simple match search
            best_match_len = 0
            best_offset = 0
            for j in range(max(0, i - 65536), i):
                match_len = 0
                while (match_len < self.max_match and 
                       i + match_len < len(data) and 
                       data[j + match_len] == data[i + match_len]):
                    match_len += 1
                if match_len > best_match_len:
                    best_match_len = match_len
                    best_offset = i - j
            
            if best_match_len > 8:
                compressed.extend(b'\xFF')
                compressed.extend(best_offset.to_bytes(4, 'little'))
                compressed.extend(best_match_len.to_bytes(2, 'little'))
                i += best_match_len
            else:
                ctx = tuple(data[max(0, i-self.context_order):i])
                pred = self.predict_byte(ctx)
                actual = data[i]
                
                if actual == pred:
                    compressed.extend(b'\xFE')
                else:
                    compressed.extend(b'\xFD')
                    compressed.append(actual)
                    self.update_context(ctx, actual)
                i += 1
        
        final = lzma.compress(bytes(compressed), preset=9)
        
        header = {
            'original_size': original_size,
            'checksum': hashlib.sha256(data).hexdigest(),
            'version': 'nexus-v0.1'
        }
        packed = pickle.dumps(header) + b'\n---NEXUS---\n' + final
        
        print(f'Nexus compressed: {original_size/1024:.1f}KB → {len(packed)/1024:.1f}KB in {time.time()-start:.2f}s')
        return packed
    
    def decompress(self, packed: bytes) -> bytes:
        header_data, compressed = packed.split(b'\n---NEXUS---\n', 1)
        header = pickle.loads(header_data)
        
        stream = lzma.decompress(compressed)
        data = bytearray()
        i = 0
        while i < len(stream):
            flag = stream[i]
            i += 1
            if flag == 0xFF:  # match
                offset = int.from_bytes(stream[i:i+4], 'little')
                length = int.from_bytes(stream[i+4:i+6], 'little')
                i += 6
                start = len(data) - offset
                data.extend(data[start:start+length])
            else:  # literal or prediction
                data.append(stream[i])
                i += 1
        
        return bytes(data)

# CLI
if __name__ == "__main__":
    if len(sys.argv) > 2:
        with open(sys.argv[1], "rb") as f:
            data = f.read()
        comp = NexusCompressor()
        packed = comp.compress(data)
        with open(sys.argv[2], "wb") as f:
            f.write(packed)