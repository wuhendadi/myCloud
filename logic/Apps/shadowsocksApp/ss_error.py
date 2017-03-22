generalErrors=((0,  "success"),
                (-1, "reserved"),
                (-2, "no default conf"),
                (-3, "network not available"),
                (-4, "route ip invalid"),
                (-5, "route port redirection failed"),
                (-6, "route unknown error"),
                (-7, "process already exist"),
                (-8, "pid file error")
               )

class GerneralError(Exception):
	def __init__(self, value):
		self.value = value
	def __str__(self):
		return repr(self.value)

         
