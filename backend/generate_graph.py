import os
from agents import create_agent_graph

def generate_graph_png():
    try:
        graph = create_agent_graph()
        # This requires the 'langgraph' library to be installed
        # and likely an internet connection or local setup for mermaid rendering if using draw_mermaid_png
        # Alternatively, draw_png might require pygraphviz.
        
        print("Generating graph...")
        png_bytes = graph.get_graph().draw_mermaid_png()
        
        output_path = os.path.join(os.path.dirname(__file__), "agent_graph.png")
        with open(output_path, "wb") as f:
            f.write(png_bytes)
            
        print(f"Graph successfully saved to {os.path.abspath(output_path)}")
        
    except Exception as e:
        print(f"Error generating graph: {e}")
        print("Ensure you have langgraph installed and internet connection for mermaid API if used.")

if __name__ == "__main__":
    generate_graph_png()

