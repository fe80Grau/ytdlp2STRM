from datetime import datetime
import argparse
import config.plugins as  plugins
from sanitize_filename import sanitize


if __name__ == "__main__":
    parser=argparse.ArgumentParser()

    parser.add_argument('--m', help='Método a ejecutar')
    parser.add_argument('--p', help='Parámetros para el método a ejecutar. Separado por comas.')

    args=parser.parse_args()

    method = args.m if args.m != None else "error"
    params = args.p.split(',') if args.p != None else None
    
    # Keep working for old version
    if method == "make_filest_strm":
        method = "plugins.youtube.to_strm"
    if args.p == "youtube,redirect":
        params = ["youtube", "direct"]
    if args.p == "youtube,stream":
        params = ["youtube", "bridge"]
    # --

    now = datetime.now()
    dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
    print(dt_string)
    print("Running {} with {} params".format(method, params))
    r = False
    if params != None:
        r = eval(method)(*params)
    else:
        r = eval(method)