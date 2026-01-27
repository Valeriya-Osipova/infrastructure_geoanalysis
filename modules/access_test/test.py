import sys
import os

# Добавляем родительскую директорию в путь Python
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from accessibility_module import analyze_accessibility

house_coord = (34.569816745664845, 61.631042923709295)
result = analyze_accessibility(house_coord)
print(result)