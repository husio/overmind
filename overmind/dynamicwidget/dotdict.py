class Dict(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            msg = '"{}" instance does not have {} attribute'.format(
                    type(self).__name__, name)
            raise AttributeError(msg)
