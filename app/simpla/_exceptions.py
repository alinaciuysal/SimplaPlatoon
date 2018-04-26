class SimplaException(Exception):
    '''
    Simple exception raised by simpla.
    '''
    def __init__(self,*args,**kwargs):
        super(SimplaException, self).__init__(*args,**kwargs)