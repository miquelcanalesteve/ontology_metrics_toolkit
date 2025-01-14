from rdflib import Graph, RDF, RDFS, OWL, URIRef, Literal, Namespace, BNode
import pandas as pd
import os
import re
from transformers import AutoTokenizer

def identify_classes(g):
    """
    Identifies all resources that can be considered classes.
    Prioritizes explicit classes and only infers classes if no explicit ones are found.
    Removes datatypes defined as "rdfs:Datatype" or originating from "xsd:".

    Excludes certain RDF, RDFS, and OWL entities from being identified as classes.

    :param g: RDF graph.
    :return: Dictionary with classes as keys and identification details as values.
    """
    classes = {}
    XSD = Namespace("http://www.w3.org/2001/XMLSchema#")
    RDF_CLASS = URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#Class")

    # OWL terms to exclude
    OWL_EXCLUDES = {
        OWL.Ontology,
        OWL.Restriction,
        OWL.DeprecatedClass,
        OWL.ObjectProperty,
        OWL.TransitiveProperty,
        OWL.DatatypeProperty,
        OWL.FunctionalProperty,
        OWL.DeprecatedProperty,
        OWL.Thing,
        OWL.Nothing,
        OWL.AnnotationProperty,
        OWL.SymmetricProperty,
        OWL.InverseFunctionalProperty,
    }

    # Additional exclusions
    ADDITIONAL_EXCLUDES = {
        URIRef("http://www.w3.org/2000/01/rdf-schema#Class"),
        URIRef("http://www.w3.org/2002/07/owl#Class"),
        URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#Property"),
    }

    # 1. Detect explicit classes via RDF.type OWL.Class
    for s, p, o in g.triples((None, RDF.type, OWL.Class)):
        if s not in ADDITIONAL_EXCLUDES:
            classes[s] = {"type": "explicit (RDF.type OWL.Class)"}

    # 2. Detect explicit classes via RDF.type RDFS.Class
    for s, p, o in g.triples((None, RDF.type, RDFS.Class)):
        if s not in ADDITIONAL_EXCLUDES:
            classes[s] = {"type": "explicit (RDF.type RDFS.Class)"}

    # 3. Detect explicit classes via RDF.type rdf:Class
    for s, p, o in g.triples((None, RDF.type, RDF_CLASS)):
        if s not in ADDITIONAL_EXCLUDES:
            classes[s] = {"type": "explicit (RDF.type rdf:Class)"}

    # 4. Infer classes from Turtle syntax (resources after 'a')
    for s, p, o in g.triples((None, RDF.type, None)):
        if o not in classes:  # Only add if not explicitly defined as a class
            if (o in OWL_EXCLUDES or 
                o in ADDITIONAL_EXCLUDES or
                str(o).startswith(str(XSD)) or 
                o in {RDFS.Datatype, RDFS.Resource, RDFS.Literal}):
                continue  # Skip OWL exclusions, XSD datatypes, and RDFS exclusions
            classes[o] = {"type": "inferred (Turtle 'a')"}
    
    # Remove classes that are of type BNode
    for cls in list(classes.keys()):
        if isinstance(cls, BNode):
            del classes[cls]
    

    return classes

def calculate_totals_and_densities(concept_properties, g, n_classes):
    """
    Calculates the total, unique number of properties and densities.

    :param concept_properties: Dictionary with properties associated with each concept.
    :param g: RDF graph.
    :param n_classes: Total number of classes.
    :return: Dictionary with calculated metrics.
    """
    all_object_properties = set()
    all_data_annotation_properties = set()

    for properties in concept_properties.values():
        for prop in properties["object_properties"]:
            all_object_properties.add(prop)

        all_data_annotation_properties.update(properties["data_annotation_properties"])

    total_object_properties_unique = len(all_object_properties)
    total_data_annotation_properties_unique = len(all_data_annotation_properties)

    total_object_properties = sum(len(properties["object_properties"]) for properties in concept_properties.values())
    total_data_annotation_properties = sum(len(properties["data_annotation_properties"]) for properties in concept_properties.values())

    # Densities
    property_density = (total_object_properties + total_data_annotation_properties) / n_classes if n_classes > 0 else 0
    object_density = total_object_properties / n_classes if n_classes > 0 else 0
    data_annotation_density = total_data_annotation_properties / n_classes if n_classes > 0 else 0

    results = {
        "total_object_properties": total_object_properties,
        "total_data_annotation_properties": total_data_annotation_properties,
        "total_object_properties_unique": total_object_properties_unique,
        "total_data_annotation_properties_unique": total_data_annotation_properties_unique,
        "property_density": property_density,
        "object_density": object_density,
        "data_annotation_density": data_annotation_density
    }
    return results

def list_properties_by_concept(file_path):
    """
    Lists the properties (Object Properties and Data/Annotation Properties) associated with each concept in a Turtle file.

    :param file_path: Path to the TTL file.
    :return: Dictionary with concepts as keys and their differentiated properties as values.
    """
    # Load the TTL file into a graph
    g = Graph()
    g.parse(file_path, format="turtle")

    # Identify classes in the graph
    classes = identify_classes(g)

    # Properties to be explicitly excluded
    excluded_object_properties = {
        URIRef("http://www.w3.org/2000/01/rdf-schema#subClassOf"),
        RDF.type
    }

    # Dictionary to store properties by concept
    concept_properties = {}

    # Iterate over the triples and associate properties with concepts
    for s, p, o in g.triples((None, None, None)):
        if s in classes:
            if s not in concept_properties:
                concept_properties[s] = {
                    "object_properties": [],
                    "data_annotation_properties": []
                }

            # Identify the type of property based on the nature of the object (o)
            if isinstance(o, URIRef) and p not in excluded_object_properties:
                # If the object is a resource (IRI) and is not in the excluded properties, it is an Object Property
                concept_properties[s]["object_properties"].append(p)
            elif not isinstance(o, URIRef) and p not in excluded_object_properties:
                # If the object is a literal, it is a Data/Annotation Property
                concept_properties[s]["data_annotation_properties"].append(p)

    # Convert property sets to lists for easier readability

    return {
        concept: {
            "type": classes[concept]["type"],  # Add the class type to the result
            "object_properties": list(properties["object_properties"]),
            "data_annotation_properties": list(properties["data_annotation_properties"]),
        }
        for concept, properties in concept_properties.items()
    }, classes

def count_subclasses_and_average(g, total_classes):
    """
    Counts the total number of unique subclasses and calculates the average number of subclasses per class.

    Removes duplicate subclass URIs and prints the unique URIs.

    :param g: RDF graph.
    :param total_classes: Total number of identified classes.
    :return: Dictionary with the total subclasses and the average per class.
    """
    subclasses = {str(s) for s, p, o in g.triples((None, RDFS.subClassOf, None))}  # Use a set to ensure uniqueness
    total_subclasses = len(subclasses)
    average_subclasses = total_subclasses / total_classes if total_classes > 0 else 0


    return {"total_subclasses": total_subclasses, "average_subclasses_per_class": average_subclasses}

def extract_textual_metrics(g):
    """
    Extracts textual metrics from the dataset, focusing on literal objects.

    :param g: RDF graph.
    :return: Dictionary with textual metrics.
    """
    literals = [o for s, p, o in g.triples((None, None, None)) if isinstance(o, Literal)]
    total_literals = len(literals)

    if total_literals == 0:
        return {
            "Total Words in Literals": 0,
            "Average Words per Literal": 0,
            "Longest Literal (Words)": 0,
            "Shortest Literal (Words)": 0,
            "Vocabulary Size in Literals": 0,
        }

    # Tokenize literals and count words
    words = []
    word_counts = []
    for literal in literals:
        tokenized = re.findall(r'\b\w+\b', str(literal))
        words.extend(tokenized)
        word_counts.append(len(tokenized))

    total_words = len(words)
    average_words_per_literal = total_words / total_literals
    longest_literal = max(word_counts)
    shortest_literal = min(word_counts)
    vocabulary = set(word.lower() for word in words)
    vocabulary_size = len(vocabulary)

    return {
        "Total Words in Literals": total_words,
        "Average Words per Literal": average_words_per_literal,
        "Longest Literal (Words)": longest_literal,
        "Shortest Literal (Words)": shortest_literal,
        "Vocabulary Size in Literals": vocabulary_size,
    }


def calculate_global_text_metrics(file_path):
    """
    Calculates global text metrics from the raw TTL file.

    :param file_path: Path to the TTL file.
    :return: Dictionary with global text metrics.
    """
    with open(file_path, "r", encoding="utf-8") as file:
        raw_text = file.read()

    # Tokenize words in the raw text
    words = re.findall(r'\b\w+\b', raw_text)
    total_words = len(words)
    vocabulary = set(word.lower() for word in words)
    vocabulary_size = len(vocabulary)

    return {
        "Total Words in Raw TTL File": total_words,
        "Vocabulary Size in Raw TTL File": vocabulary_size
    }

def count_annotation_properties(g):
    """
    Counts the number of explicitly defined annotation properties in the ontology.

    :param g: RDF graph.
    :return: Total number of annotation properties.
    """
    return sum(1 for _ in g.triples((None, RDF.type, OWL.AnnotationProperty)))

def count_datatype_properties(g):
    """
    Counts the number of explicitly defined datatype properties in the ontology.

    :param g: RDF graph.
    :return: Total number of datatype properties.
    """
    return sum(1 for _ in g.triples((None, RDF.type, OWL.DatatypeProperty)))


def count_object_properties(g):
    """
    Counts the number of explicitly defined object properties in the ontology.

    :param g: RDF graph.
    :return: Total number of object properties.
    """
    return sum(1 for _ in g.triples((None, RDF.type, OWL.ObjectProperty)))


def count_individuals(g):
    """
    Counts all individuals explicitly defined as owl:NamedIndividual and those defined as `a prefix:Class`,
    excluding those defined as `a owl:Class`, intermediate objects (e.g., blank nodes), or the ontology root.
    
    :param g: RDF graph.
    :return: Total number of individuals.
    """
    individuals = set()

    # Detect the root URI of the ontology
    ontology_root = None
    for s, p, o in g.triples((None, RDF.type, OWL.Ontology)):
        ontology_root = s
        break  # Assume there is only one subject defined as owl:Ontology

    # Exclude types related to classes and properties
    excluded_types = {
        OWL.Class, OWL.ObjectProperty, OWL.AnnotationProperty, OWL.DatatypeProperty,
        OWL.Ontology, OWL.Restriction, OWL.FunctionalProperty, OWL.DeprecatedProperty,
        OWL.InverseFunctionalProperty, OWL.SymmetricProperty, OWL.TransitiveProperty,
        OWL.onDatatype, OWL.DeprecatedClass, RDF.Property, RDFS.Datatype, RDFS.Class
    }

    def is_valid_individual(uri):
        """Checks if a URI can be considered a valid individual."""
        if ontology_root and uri == ontology_root:
            return False
        # Verify that none of the subject's types are in excluded_types
        for _, _, obj in g.triples((uri, RDF.type, None)):
            if obj in excluded_types:
                return False
        return True

    # Explicitly defined individuals as owl:NamedIndividual
    for s, p, o in g.triples((None, RDF.type, OWL.NamedIndividual)):
        if not isinstance(s, BNode) and is_valid_individual(s):  # Filter out blank nodes and invalid individuals
            individuals.add(s)

    # Individuals defined as `a prefix:Class` but not `a owl:Class`
    for s, p, o in g.triples((None, RDF.type, None)):
        if not isinstance(s, BNode) and is_valid_individual(s):
            individuals.add(s)

    return len(individuals)

def list_properties_by_individual(file_path):
    """
    Lists the properties (Object Properties and Data/Annotation Properties) associated with each individual in a Turtle file.
    Automatically detects the root URI of the ontology and excludes it from the set of individuals.

    :param file_path: Path to the TTL file.
    :return: Dictionary with individuals as keys and their differentiated properties as values, along with calculated metrics.
    """
    # Load the TTL file into a graph
    g = Graph()
    g.parse(file_path, format="turtle")

    # Detect the root URI of the ontology
    ontology_root = None
    for s, p, o in g.triples((None, RDF.type, OWL.Ontology)):
        ontology_root = s
        break  # Assume there is only one subject defined as owl:Ontology

    # Identify individuals in the graph
    individuals = set()
    excluded_types = {
        OWL.Class, OWL.ObjectProperty, OWL.AnnotationProperty, OWL.DatatypeProperty,
        OWL.Ontology, OWL.Restriction, OWL.FunctionalProperty, OWL.DeprecatedProperty,
        OWL.InverseFunctionalProperty, OWL.SymmetricProperty, OWL.TransitiveProperty,
        OWL.onDatatype, OWL.DeprecatedClass, RDF.Property, RDFS.Datatype, RDFS.Class
    }

    def is_valid_individual(uri):
        """Checks if a URI can be considered a valid individual."""
        if ontology_root and uri == ontology_root:
            return False
        # Verify that none of the subject's types are in excluded_types
        for _, _, obj in g.triples((uri, RDF.type, None)):
            if obj in excluded_types:
                return False
        return True

    # Add explicitly defined individuals as owl:NamedIndividual
    for s, p, o in g.triples((None, RDF.type, OWL.NamedIndividual)):
        if not isinstance(s, BNode) and is_valid_individual(s):
            individuals.add(s)

    # Add individuals defined as `a prefix:Class` but not `a owl:Class`
    for s, p, o in g.triples((None, RDF.type, None)):
        if o not in excluded_types and not isinstance(s, BNode) and is_valid_individual(s):
            individuals.add(s)

    # Properties to be explicitly excluded
    excluded_object_properties = {
        URIRef("http://www.w3.org/2000/01/rdf-schema#subClassOf"),
        RDF.type
    }

    # Dictionary to store properties by individual
    individual_properties = {}

    # Counters to calculate proportions
    total_object_properties = 0
    total_data_properties = 0

    # Iterate over the triples and associate properties with individuals
    for s, p, o in g.triples((None, None, None)):
        if s in individuals:
            if s not in individual_properties:
                individual_properties[s] = {
                    "object_properties": [],
                    "data_annotation_properties": []
                }

            # Identify the type of property based on the nature of the object (o)
            if (isinstance(o, URIRef) or isinstance(o, BNode)) and p not in excluded_object_properties:
                # If the object is a resource (IRI) and is not in the excluded properties, it is an Object Property
                individual_properties[s]["object_properties"].append(p)
                total_object_properties += 1
            elif not isinstance(o, URIRef) and not isinstance(o, BNode) and p not in excluded_object_properties:
                # If the object is a literal, it is a Data/Annotation Property
                individual_properties[s]["data_annotation_properties"].append(p)
                total_data_properties += 1

    # Calculate proportions
    num_individuals = len(individuals)
    object_properties_per_individual = total_object_properties / num_individuals if num_individuals > 0 else 0
    data_properties_per_individual = total_data_properties / num_individuals if num_individuals > 0 else 0
    property_density_by_individual = (
        object_properties_per_individual + data_properties_per_individual
    )

    return {
        "individual_properties": individual_properties,
        "object_properties_per_individual": object_properties_per_individual,
        "data_properties_per_individual": data_properties_per_individual,
        "property_density_by_individual": property_density_by_individual,
    }

def process_ttl_file(file_path):
    """
    Process a single TTL file and calculate the metrics.

    :param file_path: Path to the TTL file.
    :return: Dictionary with calculated metrics for the file.
    """
    try:
        # Load the graph and calculate metrics
        g = Graph()
        g.parse(file_path, format="turtle")

        # Total number of triples in the file
        total_triples = len(g)

        # Identify classes and properties
        concept_properties, classes = list_properties_by_concept(file_path)
        individuals_density= list_properties_by_individual(file_path)

        n_classes = len(classes)
        totals_and_densities = calculate_totals_and_densities(concept_properties, g, n_classes)
        subclass_metrics = count_subclasses_and_average(g, n_classes)

        num_object_properties_defined = count_object_properties(g)
        num_datatype_properties_defined = count_datatype_properties(g)
        num_annotation_properties_defined = count_annotation_properties(g)

        # Count individuals
        total_individuals = count_individuals(g)

        # Extract textual metrics from literals
        textual_metrics = extract_textual_metrics(g)

        # Calculate global text metrics from the raw TTL file
        global_text_metrics = calculate_global_text_metrics(file_path)


        # Return all metrics as a dictionary
        return {
            "File Name": os.path.basename(file_path),
            "Total Triples": total_triples,
            "Total Classes": n_classes,
            "Total Individuals": total_individuals,
            "Total Object Properties": totals_and_densities['total_object_properties'],
            "Unique Object Properties": totals_and_densities['total_object_properties_unique'],
            "Object Properties Defined":num_object_properties_defined,
            "Total Data/Annotation Properties": totals_and_densities['total_data_annotation_properties'],
            "Unique Data/Annotation Properties": totals_and_densities['total_data_annotation_properties_unique'],
            "Property Density by Class": totals_and_densities['property_density'],
            "Object Density by Class": totals_and_densities['object_density'],
            "Data/Annotation Density by Class": totals_and_densities['data_annotation_density'],
            "Property Density by Individual":individuals_density["property_density_by_individual"],
            "Object Density by Individual":individuals_density["object_properties_per_individual"],
            "Data/Annotation Density by Individual":individuals_density["data_properties_per_individual"],
            "Data Properties Defined":num_datatype_properties_defined,
            "Annotation Properties Defined":num_annotation_properties_defined,
            "Total Subclasses": subclass_metrics['total_subclasses'],
            "Average Subclasses per Class": subclass_metrics['average_subclasses_per_class'],
            "Total Words in Literals": textual_metrics["Total Words in Literals"],
            "Average Words per Literal": textual_metrics["Average Words per Literal"],
            "Longest Literal (Words)": textual_metrics["Longest Literal (Words)"],
            "Shortest Literal (Words)": textual_metrics["Shortest Literal (Words)"],
            "Vocabulary Size in Literals": textual_metrics["Vocabulary Size in Literals"],
            "Total Words in Raw TTL File": global_text_metrics["Total Words in Raw TTL File"],
            "Vocabulary Size in Raw TTL File": global_text_metrics["Vocabulary Size in Raw TTL File"]
            }

    except Exception as e:
        print(f"Error processing file {file_path}: {e}")
        return None


if __name__ == "__main__":
    # Folder containing the TTL files
    folder_path = "./ttl/ttl"  # Change this to the actual folder path
    output_excel = "ontology_metrics.xlsx"

    # Initialize an empty DataFrame
    columns = [
        "File Name", "Total Triples", "Total Classes", "Total Individuals", "Total Object Properties", "Unique Object Properties",
        "Object Properties Defined",
        "Total Data/Annotation Properties", "Unique Data/Annotation Properties",
        "Property Density by Class", "Object Density by Class", "Data/Annotation Density by Class",
        "Property Density by Individual", "Object Density by Individual", "Data/Annotation Density by Individual",
        "Data Properties Defined","Annotation Properties Defined",
        "Total Subclasses", "Average Subclasses per Class",
        "Total Words in Literals", "Average Words per Literal", "Longest Literal (Words)", "Shortest Literal (Words)",
        "Vocabulary Size in Literals", "Total Words in Raw TTL File", "Vocabulary Size in Raw TTL File"
    ]
    df = pd.DataFrame(columns=columns)

    # Process each TTL file in the folder
    for file_name in os.listdir(folder_path):
        if file_name.endswith(".ttl"):
            file_path = os.path.join(folder_path, file_name)
            print(f"Processing file: {file_name}")
            
            # Process the file and calculate metrics
            metrics = process_ttl_file(file_path)
            
            if metrics:
                # Append the results to the DataFrame
                df = pd.concat([df, pd.DataFrame([metrics])], ignore_index=True)
                
                # Save the updated DataFrame to Excel
                df.to_excel(output_excel, index=False)
                print(f"Metrics for {file_name} saved to {output_excel}")

    print(f"Processing complete. Final results saved to {output_excel}")