import re

with open('src/components/Layout.tsx', 'r') as f:
    content = f.read()

# remove unused imports from line 4
content = re.sub(r'User, Menu, X, ChevronDown, Search, Bell, Moon, Sun ', '', content)
content = re.sub(r'import { cn } from \'@/lib/utils\'\n', '', content)

# remove navigation array
content = re.sub(r'const navigation = \[\n(?:.*\n)*?\]\n', '', content)

# remove unused state and functions
content = re.sub(r'  const \[mobileMenuOpen, setMobileMenuOpen\] = useState\(false\)\n', '', content)
content = re.sub(r'  const \[userMenuOpen, setUserMenuOpen\] = useState\(false\)\n', '', content)
content = re.sub(r'  const \[theme, setTheme\] = useState<\'light\' \| \'dark\'>\(\'light\'\)\n', '', content)

content = re.sub(r'  const toggleTheme = \(\) => \{\n(?:.*\n)*?  \}\n', '', content)
content = re.sub(r'  const isActive = \(href: string\) => location\.pathname === href \|\| \(href !== \'/dashboard\' && location\.pathname\.startsWith\(href\)\)\n', '', content)

with open('src/components/Layout.tsx', 'w') as f:
    f.write(content)
print("Removed unused imports and variables")
