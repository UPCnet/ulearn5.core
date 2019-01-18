import time

# ONLY WORKS WITH *ONE* ZServer thread

ts_start = None

def log_single(event, prefix):
    global ts_start

    if prefix == 'before':
        ts_start = time.time()
    print prefix, event.name, event.handler
    if prefix == 'after':
        duration = time.time() - ts_start
        if duration > 0.5:
            print '!!!Duration: {}'.format(duration)
        else:
            print 'Duration: {}'.format(duration)
        duration = None

def handle_before_single(event):
    log_single(event, 'before')

def handle_after_single(event):
    log_single(event, 'after')

def handle_before_transforms(event):
    print 'before transforms', event

def handle_after_transforms(event):
    print 'after transforms', event
