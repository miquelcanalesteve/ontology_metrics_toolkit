# Ontology Metrics Toolkit


## Overview
**Ontology Metrics Toolkit** is a Python-based tool for analyzing and evaluating RDF/OWL ontologies, with a primary focus on Turtle (`.ttl`) format files. This toolkit calculates and summarizes various metrics to assess the structure, content, and quality of ontologies, outputting the results to an Excel file for easy analysis and further processing.

## Features
- **Component Identification**:
  - Classes, subclasses, individuals.
  - Object properties, data properties, and annotation properties.
- **Metrics Calculation**:
  - Property density by class and individual.
- **Textual Analysis**:
  - Word counts, vocabulary size, and other literal-based metrics.
- **Global Metrics**:
  - Comprehensive statistics extracted from raw `.ttl` files.

## Requirements
- **Python 3.x**
- Dependencies:
  - `rdflib`
  - `pandas`
  - `transformers`
  - `re`

Install the dependencies using:
```bash
pip install rdflib pandas transformers
```

## How to Use
1. **Prepare your ontology files**:
   - Place your Turtle (`.ttl`) files in the folder `./ttl/ttl` (or update the file path in the script).
2. **Run the script**:
   - Execute the script to process the `.ttl` files and generate metrics.
3. **Analyze the results**:
   - Metrics are saved in an Excel file named `ontology_metrics.xlsx` in the working directory.

### Example Usage
```bash
python main.py
```

## Outputs
The toolkit generates an Excel file containing:
- Total triples, classes, individuals, and properties.
- Property density and subclass metrics.
- Textual metrics from literals and raw files.
- Combined metrics for ontology evaluation.

## Getting Started
1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/ontology-metrics-toolkit.git
   ```
2. Navigate to the project directory:
   ```bash
   cd ontology-metrics-toolkit
   ```
3. Place your `.ttl` files in the appropriate folder and run the script.

## License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contributing
Contributions are welcome! If you have ideas for improvement, please open an issue or submit a pull request.

## Contact
For any inquiries or feedback, feel free to reach out via GitHub Issues or email at mikel.canal@ua.es.
