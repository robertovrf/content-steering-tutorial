class DashParser:
    def __init__(self):
        pass


    def build(self, tar, nos, uri, req):
        message = {
            'VERSION': 1,
            'TTL': 10,
            'RELOAD-URI': f'{uri}{req.path}',
            'PATHWAY-PRIORITY': nos + ['cloud'],
            'PATHWAY-CLONES': []
        }

        if nos:
            message['PATHWAY-CLONES'] = self.pathway_clones(nos)
        
        return message


    def pathway_clones(self, nos):        
        return [
            {
                'BASE-ID': f'cloud',
                'ID': no,
                'URI-REPLACEMENT': {
                    'HOST': f'https://{no}'
                }
            } for no in nos
        ]
    
parser = DashParser()