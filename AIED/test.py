def print_dict(d, indent=0):
    for k, v in d.items():
        print(' ' * indent + f'{k}:', end=' ')
        if isinstance(v, dict):
            print()
            print_dict(v, indent + 4)
        elif isinstance(v, list):
            print()
            for item in v:
                if isinstance(item, dict):
                    print_dict(item, indent + 4)
                else:
                    print(' ' * (indent + 4) + str(item))
        else:
            print(v)
    print()