



def close_subgraph(con_comp, sg):
    closed_comp = []
    all_other_lines = {f.id(): [f['startnode'], f['endnode']] for f in sg.make_neg_selection('formofway', 'Dual Carriageway')}
    for dc_points in con_comp:
        dc_lines = sg.get_lines_from_nodes(con_comp[-1])
        candidate_lines = [fid for fid, endpoints in all_other_lines.items() if endpoints[0] in dc_points and endpoints[1] in dc_points]
        feat = [sg.features[fid] for fid in dc_lines + candidate_lines]
        sg.subgraph()


        other_lines = []

        pass

def get_contour_points(subgraph):
    pass

def draw_medial_axis(mid_points_sorted):
    pass