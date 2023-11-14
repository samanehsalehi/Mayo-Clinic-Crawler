import re
import json
import csv
pattern = r'has_symptom([\w\s]+?)(?=,|\.|and|or)'

# Read obo file & create a dic from each term
def read_obo(path) -> list:
    with open(path, encoding='utf-8') as fp:
        for line in fp:
            if '[Term]' not in line:
                continue
            entry = {}
            while True:
                line = next(fp)
                if not line.strip():
                    break
                [key, value] = line.split(':', 1)
                if key == 'def': # Find all matches using the regular expression
                    symptoms = re.findall(pattern, line)
                    if symptoms:
                        entry.setdefault('symptom', list())
                        for symptom in symptoms:
                            entry['symptom'].append(symptom.strip())
                    continue
                if key == 'synonym': #Add synonym term to the name to have list of possible name
                    entry['name'].append(value.strip())
                    continue
                entry.setdefault(key, list())
                entry[key].append(value.strip())
            yield entry

# open the outputfile of the parser of the scraper 
def open_output_mayo(path):
    data = ''
    with open(path) as fp:
        data = json.load(fp)  # mayoclinic
        return data

# find symptoms in the outputfile using "symptom.obo" 
def map_symp_disease(mayo_data, symps_obo) -> list:
    for disease in mayo_data:
        disease_symp = {}
        disease_symp.setdefault(disease['title'], list())
        for symp in symps_obo:
            for name in symp['name']:
                if name.lower() in disease['symptoms'].lower() and name.lower()!= 'symptom':
                   disease_symp[disease['title']].append(name.lower()) 
                   break
        yield  disease_symp

# Add doid Id symp and is_a from doid.obo
def map_symp_disease_doid(symp_disease, doid_obo):
    for doid_term in doid_obo:
        matched = 0 
        for name in doid_term['name']:#check nme and synonyms of doid term in results_map if find one then exit
            for disease in symp_disease:   
                if  next(iter(disease.keys())).lower()  == name.lower():
                    matched = 1
                    # print(name)
                    if 'symptom' in doid_term:
                        union_symp = list(set(next(iter(disease.values()))+doid_term['symptom'])) # Union two list of symptom from doid and Mayo
                        disease[next(iter(disease.keys()))] = union_symp
                    disease.setdefault('id',list())
                    disease.setdefault('is_a',list())
                    disease['id'].append(doid_term['id'][0])
                    if 'is_a' in doid_term:
                        disease['is_a'].extend(doid_term['is_a'])
                    else:
                        disease['is_a'].extend([])                    
                    break
            if matched:
                break
            if not matched:
                new_disease = {}
                if 'symptom' in doid_term:
                    new_disease[doid_term['name'][0]] = doid_term['symptom']
                else:
                    new_disease[doid_term['name'][0]] =[]
                new_disease['id'] = doid_term['id']
                if 'is_a' in doid_term:
                    new_disease['is_a'] = doid_term['is_a']
                else:
                    new_disease['is_a'] = []
                symp_disease.append(new_disease)
                break
    return symp_disease

# add sympID for each symptom
def map_symp_disease_doid_symp(symp_disease_doid, symps_obo) -> list:
    for disease in symp_disease_doid:
        symptoms = next(iter(disease.values()))# Find the value of the first item in the dic
        for i,symptom in enumerate(symptoms):
            for symp_obo in symps_obo: # Search in symps list generated from symp.obo file to find sympID
                symp_names = symp_obo['name']
                for symp_name in symp_names:
                    if symp_name.rstrip('s') == symptom.rstrip('s'):
                        disease[next(iter(disease.keys()))][i] = symptom+' '+symp_obo['id'][0]
    return symp_disease_doid

# Save result as csv file 
def save_to_csv(symp_disease_doid_symp):
    # Open a CSV file in write mode with a comma separator
    with open('csv_output.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile, delimiter=',')

        writer.writerow(['Disease', 'DOIDId', 'Symptom', 'SymptomId'])

        for entry in symp_disease_doid_symp:
            disease_name = list(entry.keys())[0]
            if 'id' in entry.keys():
                disease_id = entry["id"][0]
                symptoms = entry[disease_name]

                for symptom in symptoms:
                    if "SYMP:" in symptom:
                        symptom_name = symptom.split("SYMP:")[0]
                        symptom_code = symptom.split("SYMP:")[1]
                        writer.writerow([disease_name, disease_id, symptom_name, f'SYMP:{symptom_code}'])
                if 'is_a' in entry.keys():
                    is_a_s = entry['is_a']
                    for is_a in is_a_s:
                        writer.writerow([disease_name, disease_id, 'is_a', is_a.split('!')[0].strip()])





def main() -> None:
    mayo_data = open_output_mayo('./output-symps.json')
    doid_obo = list(read_obo('./doid.obo'))
    symps_obo = list(read_obo('./symp.obo'))
    results_map_symp_disease = list(map_symp_disease(mayo_data, symps_obo))
    with open('symp_mayo_map.json', 'w') as jf:
        json.dump(results_map_symp_disease, jf, ensure_ascii=False, indent=4)
    results_map_symp_disease_doid = map_symp_disease_doid(results_map_symp_disease, doid_obo)
    with open('doid_symp_mayo_map.json', 'w') as jf:
        json.dump(results_map_symp_disease_doid, jf, ensure_ascii=False, indent=4)
    result_map_symp_disease_doid_symp = map_symp_disease_doid_symp(results_map_symp_disease_doid, symps_obo)
    with open ('doid_symp_mayo_sympID_map.json', 'w') as jf:
        json.dump(result_map_symp_disease_doid_symp,jf, ensure_ascii=False, indent=4)
    save_to_csv(result_map_symp_disease_doid_symp)
if __name__ == '__main__':
    raise SystemExit(main())

