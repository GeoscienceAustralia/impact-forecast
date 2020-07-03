#!/usr/bin/env python
# coding: utf-8

from graphviz import Digraph, render, nohtml

g = Digraph("Impact forecasting workflow", filename="impact_workflow.gv")
g.attr(rankdir='UD')
g.attr(compound='true')
g.attr(labeljust="l")
g.attr(fontname="Arial")


source_atts = {"shape": "invhouse",
               "style": 'filled',
               "fillcolor": 'green'}

product_atts = {"shape": "invhouse",
               "style": 'filled',
               "fillcolor": 'red',
               "fontname": "Arial",
               "penwidth": "2"}

att_atts = {"shape": "Mrecord",
            "style": "filled",
            "fillcolor": "white",
            "fontname": "Arial",
            "fontsize": "10"}

subprocess_atts = {"shape": "box3d",
                   "style": "filled",
                   "penwidth": "2",
                   "fillcolor": "aquamarine3",
                   "fontname": "Arial",
                   "fontsize": "9"}

process_atts = {"shape": "box3d",
                   "style": "filled",
                   "penwidth": "2",
                   "fillcolor": "aquamarine3"}
data_atts = {"shape": "box",
             "style": "filled",
             "fillcolor": "royalblue"}

template_atts = {"shape": "tab",
                 "fontname": "Arial",
                 "fontsize": "10"}

with g.subgraph(name="cluster_haz") as h:
    h.attr(label="Hazard information")
    h.node("ACCESS-City data", **source_atts)
    h.node("Forecast time", **att_atts)
    h.node("Forecast domain", 'Forecast domain\n "SY"',  **att_atts)
    h.node("HazImp wind template", 'HazImp template\n"template: wind_nc"', **template_atts)
    with h.subgraph(name="cluster_haz_extraction") as s:
        s.attr(label="Extraction", fontname="Arial", fontsize="10")
        s.node("Hazard layer", **data_atts)
        s.node("Extract var","Extract variable\n'wndgust10m'", **subprocess_atts)
        s.edge("Extract var", "Hazard layer")

    h.edge("ACCESS-City data", "Extract var", lhead="cluster_haz_extraction", )
    h.edges([("ACCESS-City data", "Forecast time"),
             ("ACCESS-City data", "Forecast domain")])
    
with g.subgraph(name="cluster_agg") as a:
    a.node("AggSource", "Aggregation boundaries", **source_atts)
    a.node("AggBdyFile", "Aggregation boundary file name", **att_atts)
    a.node("AggBdyField", "Aggregation boundary field name", **att_atts)
    a.edges([("AggSource", "AggBdyFile"),
             ("AggSource", "AggBdyField")])
    a.attr(label="Aggregation information")


    
g.node("ga-aws-tcrm-hazimp-nonprod", label="Exposure data", **source_atts)

g.node("NEXIS extraction", **process_atts)
g.edge("Forecast domain", "NEXIS extraction")
g.edge("ga-aws-tcrm-hazimp-nonprod", "NEXIS extraction")

g.node("Output file name", **att_atts)

with g.subgraph(name="cluster_config") as c:
    c.attr(label="HazImp Configuration", style="filled", fillcolor="lightblue", labeljust="l")
    c.node("Configuration file", shape="component", style="filled", fontname="Arial", fontsize="10", fillcolor="grey")
    c.edge("AggBdyFile", "Configuration file")
    c.edge("AggBdyField", "Configuration file")
    c.edge("HazImp wind template", "Configuration file")


g.node("HazImp", label="HazImp engine", **process_atts)


g.edge("Forecast time", "Output file name")
g.edge("Forecast domain", "Output file name")
g.edge("Output file name", "Configuration file")
g.edge("NEXIS extraction", "HazImp")
g.edge("Hazard layer", "HazImp")
g.edge("Configuration file", "HazImp")

with g.subgraph(name="cluster_output") as o:
    o.attr(label="HazImp output files")
    o.node("Shape file")
    o.node("GeoJSON")
    o.node("PROV XML")

g.edge("HazImp", "Shape file", lhead="cluster_output")
g.edge("HazImp", "GeoJSON", lhead="cluster_output")
g.edge("HazImp", "PROV XML", lhead="cluster_output")

g.node("Delivery", **product_atts)
g.edge("GeoJSON", "Delivery")
g.edge("Shape file", "Delivery")
g.render(format="svg")

