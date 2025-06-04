

import numpy as np


def poisson_per_time(total_time, rate_per_minute):
    return np.random.exponential(
        1/(rate_per_minute / 60), 
        int(total_time * rate_per_minute)
    )


def zipf(total_videos, samples, alpha):
    zipf_dist = [1.0 / (i ** alpha) for i in range(1, total_videos + 1)]
    zipf_dist = [x / sum(zipf_dist) for x in zipf_dist]

    indices = np.random.choice(total_videos, samples, p=zipf_dist)
    data = np.random.permutation(np.arange(1, total_videos + 1))

    return [data[i] for i in indices]
