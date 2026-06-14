import re

with open('src/components/Layout.tsx', 'r') as f:
    content = f.read()

# We know the first return block starts at line 85: "  return (\n    <div className=\"min-h-screen bg-background\">"
# and ends at line 245: "    </div>\n  )\n}"
# The second return block is from 248: "  return (\n    <div className=\"min-h-screen bg-background font-sans text-slate-900\">"
# to 318: "    </div>\n  )\n}"

pattern = r"  return \(\n    <div className=\"min-h-screen bg-background\">.*?(?=  return \(\n    <div className=\"min-h-screen bg-background font-sans text-slate-900\">)"

# let's just do a specific replace
lines = content.split('\n')
start1 = -1
end1 = -1
start2 = -1

for i, line in enumerate(lines):
    if 'return (' in line and 'bg-background' in lines[i+1] and 'font-sans' not in lines[i+1]:
        start1 = i
    if 'return (' in line and 'font-sans text-slate-900' in lines[i+1]:
        start2 = i
        
for i in range(start1, start2):
    if lines[i] == '}':
        end1 = i

if start1 != -1 and start2 != -1 and end1 != -1:
    new_lines = lines[:start1] + lines[start2:]
    with open('src/components/Layout.tsx', 'w') as f:
        f.write('\n'.join(new_lines))
    print("Fixed layout")
else:
    print(f"Failed to find indices: {start1}, {end1}, {start2}")

