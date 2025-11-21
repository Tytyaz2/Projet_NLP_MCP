from server import server

# Tester analyze_file sur un fichier
result = server.tools["analyze_file"]("/dataset/2020_Retinal Image Segmentation with a Structure-Texture Demixing Network_Zhang (8).pdf")
print(result)

# Tester group_files avec un résultat fictif
groups = server.tools["group_files"]([result])
print(groups)

# Appliquer le plan de déplacement
#apply_result = server.tools["apply_file_plan"]("/data", groups["groups"])
#print(apply_result)
