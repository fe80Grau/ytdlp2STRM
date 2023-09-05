from datetime import datetime
import argparse
import config.plugins as  plugins
from sanitize_filename import sanitize

def main(raw_args=None):
    parser=argparse.ArgumentParser()

    parser.add_argument('-m', '--media', help='Media platform')
    parser.add_argument('-p', '--params', help='Params to media platform mode.')
    # Keep working for old version
    parser.add_argument('--m', help='Media platform (old)')
    parser.add_argument('--p', help='Params to media platform mode (old)')
    # --

    args=parser.parse_args(raw_args)
    method = args.media if args.media != None else "error"
    params = args.params.split(',') if args.params != None else None

    # Keep working for old version
    if method == "error":
        method = args.m if args.m != None else "error"
    if params == None:
        params = args.p.split(',') if args.p != None else None


    if "plugins" in method:
        method = method.split('.')[1]
    if method == "make_files_strm":
        method = "youtube"
    if "twitch" in params:
        params = [params[1]]
    if 'redirect' in params:
        params = ["direct"]
    if 'stream' in params:
        params = ["bridge"]
    # --

    now = datetime.now()
    dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
    print(dt_string)
    print("Running {} with {} params".format(method, params))
    r = False
    if params != None:
        r = eval("{}.{}.{}".format("plugins",method,"to_strm"))(*params)

if __name__ == "__main__":
    main()