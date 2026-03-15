"""Generate a LangFlow-importable JSON flow that mirrors the LangGraph mutation research workflow.

Run:
    python generate_langflow_json.py

Produces:
    ../mutation_research_flow.json
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path


def _short_id() -> str:
    return uuid.uuid4().hex[:5]


# ---------------------------------------------------------------------------
# Minimal component builders
# ---------------------------------------------------------------------------

def _make_chat_input(node_id: str, x: float, y: float) -> dict:
    return {
        "data": {
            "id": node_id,
            "description": "Get chat inputs from the Playground.",
            "display_name": "Chat Input",
            "node": {
                "base_classes": ["Message"],
                "description": "Get chat inputs from the Playground.",
                "display_name": "Chat Input",
                "icon": "MessagesSquare",
                "outputs": [
                    {"display_name": "Chat Message", "name": "message", "types": ["Message"], "method": "message_response", "selected": "Message", "cache": True, "value": "__UNDEFINED__"}
                ],
                "template": {
                    "_type": "Component",
                    "input_value": {"type": "str", "name": "input_value", "display_name": "Input Text", "value": "", "show": True, "multiline": True, "input_types": [], "required": False, "advanced": False},
                    "should_store_message": {"type": "bool", "name": "should_store_message", "display_name": "Store Messages", "value": True, "show": True, "advanced": True},
                    "sender": {"type": "str", "name": "sender", "display_name": "Sender Type", "value": "User", "options": ["Machine", "User"], "show": True, "advanced": True},
                    "sender_name": {"type": "str", "name": "sender_name", "display_name": "Sender Name", "value": "User", "show": True, "advanced": True, "input_types": ["Message"]},
                    "session_id": {"type": "str", "name": "session_id", "display_name": "Session ID", "value": "", "show": True, "advanced": True, "input_types": ["Message"]},
                },
            },
            "type": "ChatInput",
        },
        "id": node_id,
        "position": {"x": x, "y": y},
        "type": "genericNode",
    }


def _make_prompt(node_id: str, display_name: str, template_text: str, x: float, y: float) -> dict:
    return {
        "data": {
            "id": node_id,
            "description": f"Prompt: {display_name}",
            "display_name": display_name,
            "node": {
                "base_classes": ["Message"],
                "description": f"Prompt: {display_name}",
                "display_name": display_name,
                "icon": "prompts",
                "custom_fields": {"template": []},
                "outputs": [
                    {"display_name": "Prompt", "name": "prompt", "types": ["Message"], "method": "build_prompt", "selected": "Message", "cache": True, "value": "__UNDEFINED__"}
                ],
                "template": {
                    "_type": "Component",
                    "template": {"type": "prompt", "name": "template", "display_name": "Template", "value": template_text, "show": True, "advanced": False},
                },
            },
            "type": "Prompt",
        },
        "id": node_id,
        "position": {"x": x, "y": y},
        "type": "genericNode",
    }


def _make_llm(node_id: str, display_name: str, system_message: str, x: float, y: float) -> dict:
    return {
        "data": {
            "id": node_id,
            "description": f"LLM: {display_name}",
            "display_name": display_name,
            "node": {
                "base_classes": ["LanguageModel", "Message"],
                "description": f"LLM: {display_name}",
                "display_name": display_name,
                "icon": "brain-circuit",
                "outputs": [
                    {"display_name": "Model Response", "name": "text_output", "types": ["Message"], "method": "text_response", "selected": "Message", "cache": True, "value": "__UNDEFINED__"},
                    {"display_name": "Language Model", "name": "model_output", "types": ["LanguageModel"], "method": "build_model", "selected": "LanguageModel", "cache": True, "value": "__UNDEFINED__"},
                ],
                "template": {
                    "_type": "Component",
                    "model": {"type": "str", "name": "model", "display_name": "Language Model", "value": "", "show": True, "advanced": False, "input_types": ["LanguageModel"], "_input_type": "ModelInput", "required": True, "real_time_refresh": True},
                    "api_key": {"type": "str", "name": "api_key", "display_name": "API Key", "value": "", "show": True, "advanced": True, "password": True, "_input_type": "SecretStrInput"},
                    "input_value": {"type": "str", "name": "input_value", "display_name": "Input", "value": "", "show": True, "advanced": False, "input_types": ["Message"], "_input_type": "MessageInput"},
                    "system_message": {"type": "str", "name": "system_message", "display_name": "System Message", "value": system_message, "show": True, "advanced": False, "multiline": True},
                    "stream": {"type": "bool", "name": "stream", "display_name": "Stream", "value": False, "show": True, "advanced": True},
                    "temperature": {"type": "float", "name": "temperature", "display_name": "Temperature", "value": 0.2, "show": True, "advanced": True},
                    "max_tokens": {"type": "int", "name": "max_tokens", "display_name": "Max Tokens", "value": 2048, "show": True, "advanced": True},
                },
            },
            "type": "LanguageModelComponent",
        },
        "id": node_id,
        "position": {"x": x, "y": y},
        "type": "genericNode",
    }


def _make_chat_output(node_id: str, x: float, y: float) -> dict:
    return {
        "data": {
            "id": node_id,
            "description": "Display a chat message in the Playground.",
            "display_name": "Chat Output",
            "node": {
                "base_classes": ["Message"],
                "description": "Display a chat message in the Playground.",
                "display_name": "Chat Output",
                "icon": "MessagesSquare",
                "outputs": [
                    {"display_name": "Output Message", "name": "message", "types": ["Message"], "method": "message_response", "selected": "Message", "cache": True, "value": "__UNDEFINED__"}
                ],
                "template": {
                    "_type": "Component",
                    "input_value": {"type": "str", "name": "input_value", "display_name": "Inputs", "value": "", "show": True, "advanced": False, "input_types": ["Data", "JSON", "DataFrame", "Table", "Message"], "required": True, "_input_type": "MessageInput"},
                    "should_store_message": {"type": "bool", "name": "should_store_message", "display_name": "Store Messages", "value": True, "show": True, "advanced": True},
                    "sender": {"type": "str", "name": "sender", "display_name": "Sender Type", "value": "Machine", "options": ["Machine", "User"], "show": True, "advanced": True},
                    "sender_name": {"type": "str", "name": "sender_name", "display_name": "Sender Name", "value": "AI", "show": True, "advanced": True, "input_types": ["Message"]},
                    "session_id": {"type": "str", "name": "session_id", "display_name": "Session ID", "value": "", "show": True, "advanced": True, "input_types": ["Message"]},
                    "data_template": {"type": "str", "name": "data_template", "display_name": "Data Template", "value": "{text}", "show": True, "advanced": True, "input_types": ["Message"]},
                },
            },
            "type": "ChatOutput",
        },
        "id": node_id,
        "position": {"x": x, "y": y},
        "type": "genericNode",
    }


def _make_edge(source_id: str, source_type: str, source_output: str, source_output_types: list[str],
               target_id: str, target_type: str, target_field: str, target_input_types: list[str]) -> dict:
    return {
        "animated": False,
        "data": {
            "sourceHandle": {"dataType": source_type, "id": source_id, "name": source_output, "output_types": source_output_types},
            "targetHandle": {"fieldName": target_field, "id": target_id, "inputTypes": target_input_types, "type": "str"},
        },
        "id": f"reactflow__edge-{source_id}-{target_id}-{target_field}-{_short_id()}",
        "source": source_id,
        "sourceHandle": json.dumps({"dataType": source_type, "id": source_id, "name": source_output, "output_types": source_output_types}),
        "target": target_id,
        "targetHandle": json.dumps({"fieldName": target_field, "id": target_id, "inputTypes": target_input_types, "type": "str"}),
    }


# ---------------------------------------------------------------------------
# Prompt texts (from LangGraph code)
# ---------------------------------------------------------------------------

HYPOTHESIS_JSON_SCHEMA = """\
{
  "summary": "<concise hypothesis text>",
  "mechanism": "<biological mechanism or null>",
  "risk_assessment": "<risk description or null>",
  "recommendations": "<actionable items or null>",
  "confidence": <float 0-1>,
  "citations": ["<url or ref id>", ...]
}"""

PERSONAS = [
    ("clinical", "Clinical Expert specializing in disease risk assessment. Focus on how the mutation influences disease susceptibility, prognosis, and clinical outcomes."),
    ("neuro", "Neuroscience and Mental Health Expert. Focus on the mutation's impact on neurotransmitter pathways, cognitive function, and psychiatric conditions."),
    ("pharmacogenomics", "Pharmacogenomicist specializing in drug-gene interactions. Focus on how the mutation affects drug metabolism, efficacy, adverse reactions, and dosing considerations."),
    ("structural", "Structural Biologist focused on protein impact analysis. Focus on how the mutation alters protein structure, folding, stability, and functional domains."),
    ("datascience", "Data Scientist focused on population-level trends. Focus on allele frequencies, population stratification, GWAS associations, and epidemiological patterns."),
]


def _persona_system_msg(role_description: str) -> str:
    return (
        f"You are a {role_description}\n"
        "Analyze the mutation research evidence provided below and produce a single hypothesis.\n"
        "Base your analysis ONLY on the evidence given. Do not fabricate sources.\n"
        f"Respond with valid JSON matching this schema:\n{HYPOTHESIS_JSON_SCHEMA}"
    )


JUDGE_SYSTEM_MSG = (
    "You are the Chief Scientist and Judge. "
    "Your task is to compare multiple mutation-analysis hypotheses, "
    "rank them by evidence strength, internal consistency, and safety, "
    "and decide whether the overall evidence is sufficient for a confident answer.\n\n"
    "Ranking criteria:\n"
    "1. Evidence strength - how well the hypothesis is supported by cited sources.\n"
    "2. Internal consistency - logical coherence of the analysis.\n"
    "3. Safety - does the hypothesis avoid overclaiming or harmful advice.\n"
    "4. Novelty - does it contribute unique and useful insight.\n\n"
    "Set meets_threshold to true only if you judge the top hypothesis to be "
    "supported with moderate-to-strong evidence (confidence >= 0.5 and well-cited).\n\n"
    "Respond with valid JSON matching this schema:\n"
    "{\n"
    '  "ranked_hypotheses": [<list of Hypothesis objects ordered best-first>],\n'
    '  "selected_index": <int, 0-based index of the best hypothesis>,\n'
    '  "reasoning": "<explanation of ranking and selection>",\n'
    '  "meets_threshold": <bool, true if evidence is strong enough>\n'
    "}"
)

RESPONSE_SYSTEM_MSG = (
    "You are a helpful scientific research assistant. "
    "Synthesize the expert analyses below into a clear, conversational answer "
    "for the user. Be accurate, cite sources when possible, and note any limitations. "
    "Do NOT provide clinical diagnoses or definitive medical advice. "
    "If the evidence is limited, clearly state that the answer is best-effort "
    "and should be interpreted with caution."
)


# ---------------------------------------------------------------------------
# Flow builder
# ---------------------------------------------------------------------------

def build_flow() -> dict:
    nodes: list[dict] = []
    edges: list[dict] = []

    # ── 1. Chat Input ──────────────────────────────────────────────────
    chat_in_id = f"ChatInput-{_short_id()}"
    nodes.append(_make_chat_input(chat_in_id, x=0, y=400))

    # ── 2. Evidence / Search agent (LLM-based approximation) ──────────
    evidence_prompt_id = f"Prompt-ev{_short_id()}"
    nodes.append(_make_prompt(
        evidence_prompt_id,
        "Evidence Builder Prompt",
        (
            "You are a Lead Researcher and evidence gatherer. "
            "Given the user's mutation question below, produce a structured summary of "
            "key scientific evidence including:\n"
            "- Relevant literature findings (PubMed, bioRxiv)\n"
            "- Variant annotations (allele frequency, clinical significance)\n"
            "- Known disease associations\n"
            "- Protein/pathway impacts\n\n"
            "Be thorough and cite plausible sources where possible.\n\n"
            "User question:\n{user_question}"
        ),
        x=400, y=400,
    ))

    evidence_llm_id = f"LanguageModelComponent-ev{_short_id()}"
    nodes.append(_make_llm(
        evidence_llm_id,
        "Evidence Search LLM",
        "You are a scientific literature search agent. Summarize evidence accurately.",
        x=800, y=400,
    ))

    # ChatInput → Evidence Prompt (user_question variable)
    edges.append(_make_edge(chat_in_id, "ChatInput", "message", ["Message"],
                            evidence_prompt_id, "Prompt", "user_question", ["Message"]))
    # Evidence Prompt → Evidence LLM (input_value)
    edges.append(_make_edge(evidence_prompt_id, "Prompt", "prompt", ["Message"],
                            evidence_llm_id, "LanguageModelComponent", "input_value", ["Message"]))

    # ── 3. Persona agents (fan-out) ───────────────────────────────────
    persona_llm_ids: list[str] = []
    persona_y_positions = [0, 200, 400, 600, 800]

    for i, (agent_id, role_desc) in enumerate(PERSONAS):
        y_pos = persona_y_positions[i]

        # Persona prompt
        p_prompt_id = f"Prompt-{agent_id[:4]}{_short_id()}"
        nodes.append(_make_prompt(
            p_prompt_id,
            f"{agent_id.capitalize()} Prompt",
            (
                f"User question:\n{{user_question}}\n\n"
                f"Evidence:\n{{evidence}}"
            ),
            x=1200, y=y_pos,
        ))

        # Persona LLM
        p_llm_id = f"LanguageModelComponent-{agent_id[:4]}{_short_id()}"
        nodes.append(_make_llm(
            p_llm_id,
            f"{agent_id.capitalize()} Expert LLM",
            _persona_system_msg(role_desc),
            x=1600, y=y_pos,
        ))
        persona_llm_ids.append(p_llm_id)

        # ChatInput → Persona Prompt (user_question)
        edges.append(_make_edge(chat_in_id, "ChatInput", "message", ["Message"],
                                p_prompt_id, "Prompt", "user_question", ["Message"]))
        # Evidence LLM → Persona Prompt (evidence)
        edges.append(_make_edge(evidence_llm_id, "LanguageModelComponent", "text_output", ["Message"],
                                p_prompt_id, "Prompt", "evidence", ["Message"]))
        # Persona Prompt → Persona LLM (input_value)
        edges.append(_make_edge(p_prompt_id, "Prompt", "prompt", ["Message"],
                                p_llm_id, "LanguageModelComponent", "input_value", ["Message"]))

    # ── 4. Combine hypotheses (fan-in prompt) ─────────────────────────
    combine_prompt_id = f"Prompt-comb{_short_id()}"

    combine_template_parts = ["User question:\n{user_question}\n\nHypotheses to evaluate:\n"]
    persona_var_names = []
    for agent_id, _ in PERSONAS:
        var_name = f"{agent_id}_hypothesis"
        persona_var_names.append(var_name)
        combine_template_parts.append(
            f"--- Hypothesis from {agent_id} ---\n"
            f"{{{var_name}}}\n"
        )
    combine_template = "\n".join(combine_template_parts)

    nodes.append(_make_prompt(
        combine_prompt_id,
        "Combine Hypotheses",
        combine_template,
        x=2000, y=400,
    ))

    # ChatInput → Combine Prompt (user_question)
    edges.append(_make_edge(chat_in_id, "ChatInput", "message", ["Message"],
                            combine_prompt_id, "Prompt", "user_question", ["Message"]))

    # Each Persona LLM → Combine Prompt (persona_hypothesis variable)
    for llm_id, var_name in zip(persona_llm_ids, persona_var_names):
        edges.append(_make_edge(llm_id, "LanguageModelComponent", "text_output", ["Message"],
                                combine_prompt_id, "Prompt", var_name, ["Message"]))

    # ── 5. Judge LLM ──────────────────────────────────────────────────
    judge_llm_id = f"LanguageModelComponent-jdg{_short_id()}"
    nodes.append(_make_llm(
        judge_llm_id,
        "Judge (Chief Scientist) LLM",
        JUDGE_SYSTEM_MSG,
        x=2400, y=400,
    ))

    # Combine Prompt → Judge LLM (input_value)
    edges.append(_make_edge(combine_prompt_id, "Prompt", "prompt", ["Message"],
                            judge_llm_id, "LanguageModelComponent", "input_value", ["Message"]))

    # ── 6. Response Composer ──────────────────────────────────────────
    response_prompt_id = f"Prompt-resp{_short_id()}"
    nodes.append(_make_prompt(
        response_prompt_id,
        "Response Composer Prompt",
        (
            "User question:\n{user_question}\n\n"
            "Judge analysis and ranked hypotheses:\n{judge_output}\n\n"
            "Compose a helpful, evidence-based, conversational response for the user."
        ),
        x=2800, y=400,
    ))

    # ChatInput → Response Prompt (user_question)
    edges.append(_make_edge(chat_in_id, "ChatInput", "message", ["Message"],
                            response_prompt_id, "Prompt", "user_question", ["Message"]))
    # Judge LLM → Response Prompt (judge_output)
    edges.append(_make_edge(judge_llm_id, "LanguageModelComponent", "text_output", ["Message"],
                            response_prompt_id, "Prompt", "judge_output", ["Message"]))

    response_llm_id = f"LanguageModelComponent-resp{_short_id()}"
    nodes.append(_make_llm(
        response_llm_id,
        "Response Composer LLM",
        RESPONSE_SYSTEM_MSG,
        x=3200, y=400,
    ))

    # Response Prompt → Response LLM (input_value)
    edges.append(_make_edge(response_prompt_id, "Prompt", "prompt", ["Message"],
                            response_llm_id, "LanguageModelComponent", "input_value", ["Message"]))

    # ── 7. Chat Output ────────────────────────────────────────────────
    chat_out_id = f"ChatOutput-{_short_id()}"
    nodes.append(_make_chat_output(chat_out_id, x=3600, y=400))

    # Response LLM → Chat Output (input_value)
    edges.append(_make_edge(response_llm_id, "LanguageModelComponent", "text_output", ["Message"],
                            chat_out_id, "ChatOutput", "input_value", ["Data", "JSON", "DataFrame", "Table", "Message"]))

    return {
        "data": {
            "nodes": nodes,
            "edges": edges,
        },
        "description": "Mutation Research Chat Agent — Fan-out/fan-in multi-persona workflow",
        "name": "Mutation Research Chat Agent",
        "endpoint_name": "mutation-research-chat",
        "is_component": False,
    }


if __name__ == "__main__":
    flow = build_flow()
    out_path = Path(__file__).resolve().parent.parent / "mutation_research_flow.json"
    out_path.write_text(json.dumps(flow, indent=2), encoding="utf-8")
    print(f"LangFlow JSON written to {out_path}")
    print(f"  Nodes: {len(flow['data']['nodes'])}")
    print(f"  Edges: {len(flow['data']['edges'])}")
