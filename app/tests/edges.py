import random
nrOfNotTravelledEdges = 5

def extract_info(edges):
    print(edges)
    # random.seed(3)
    rnd_edge = random.choice(edges[-nrOfNotTravelledEdges:])
    print("random_edge", rnd_edge)
    rnd_edge_idx = edges.index(rnd_edge) + 1 # to include randomly selected edge
    print(rnd_edge_idx)
    all_parts = edges[:rnd_edge_idx]
    print(all_parts)

if __name__ == '__main__':
    edges = ['11S', '52151764', '290409649', '290409654', '290402731', '286342699', '286342698', '116757885', 'Shoulder01', '290402735', 'Shoulder02', '286343803', '290402733', '135586672#0', '12N']
    extract_info(edges)