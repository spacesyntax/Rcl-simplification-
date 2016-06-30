
import processing
import graph_tools_1

def make_distance_matrix (points):
    # make a distance matrix of all points for the 10 closest neighbours
    # get the path of the Points layer and make the path of th csv matrix
    network_filepath = network.dataProvider().dataSourceUri()
    (myDirectory, nameFile) = os.path.split(network_filepath)
    csv_path = myDirectory + "/Matrix.csv"

    processing.runalg("qgis:distancematrix", Points, "fid", Points, "fid", 0, 10, csv_path)

    # specify new short lines as new edges
    New_edges = []

    with open(csv_path, 'rb') as f:
        reader = csv.reader(f)
        your_list = list(reader)

    # remove header
    your_list.remove(['InputID', 'TargetID', 'Distance'])

    for i in your_list:
        if float(i[2]) <= threshold_inter and float(i[2]) > 0:
            if i[0] >= i[1]:
                New_edges.append([int(i[0]), int(i[1])])


def find_inter_edges(dual_graph,inter_distance):
    pass

def find_parallel_inter (primary_graph,angle_threshold):
    pass

def find_unique_paths (primary_graph):




def fix_disconnections:

def extend_lines:
