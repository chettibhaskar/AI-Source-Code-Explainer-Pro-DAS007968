from flask import Flask, render_template, request, jsonify
from code_explainer import ProCodeExplainer
import plotly.graph_objects as go

app = Flask(__name__)
explainer = ProCodeExplainer()

@app.route('/', methods=['GET','POST'])
def index():
    result = None
    code = ""
    lang = "python"
    if request.method == 'POST':
        code = request.form.get('code','')
        lang = request.form.get('language','python')
        result = explainer.explain_multi_language(code, lang)

        # Create Flow Diagram
        if result and 'flow_nodes' in result and result['flow_nodes']:
            fig = go.Figure(data=[go.Sankey(
                node=dict(label=["Start"] + result['flow_nodes'] + ["End"]),
                link=dict(source=[0]*len(result['flow_nodes']), target=list(range(1, len(result['flow_nodes'])+1)), value=[1]*len(result['flow_nodes']))
            )])
            fig.update_layout(title_text="Code Execution Flow", font_size=12)
            result['flow_html'] = fig.to_html(full_html=False)

    return render_template('index.html', result=result, code=code, lang=lang)

@app.route('/api/explain', methods=['POST'])
def api_explain():
    data = request.json
    code = data.get('code','')
    lang = data.get('language','python')
    return jsonify(explainer.explain_multi_language(code, lang))

if __name__ == '__main__':
    app.run(debug=True, port=5000)