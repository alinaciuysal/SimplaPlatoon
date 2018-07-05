
from operator import itemgetter

def adjustInterval(intervals):
    lis = [(101, 153), (255, 827), (361, 961)]

    min_interval = min(lis, key=itemgetter(0))[0]
    max_interval = max(lis, key=itemgetter(1))[1]

    return min_interval, max_interval

if __name__ == '__main__':
    intervals = [(101, 153), (255, 827), (361, 961)]
    tpl = adjustInterval(intervals)
    print(tpl)