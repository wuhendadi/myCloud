
import time
import cherrypy
import UtilFunc
import ProfileFunc
import PopoConfig
import Log

def session_time_control():
    while True:
        len_server = len(cherrypy.engine.timeout_monitor.servings)
        for client_id, token_dict in ProfileFunc.client_token.items():
            if token_dict.get('time'):
                if (token_dict.get('upload') or token_dict.get('download')) and len_server > 0:
                    token_dict.update({'time':time.time()})
                else:
                    if int(time.time()-token_dict['time']) >= PopoConfig.SESSION_TIMEOUT:
                        Log.info("client_id is {client_id}, time is {cu_time}".format(client_id=client_id, cu_time =time.ctime() ))
                        del ProfileFunc.client_token[client_id]
        time.sleep(5)

