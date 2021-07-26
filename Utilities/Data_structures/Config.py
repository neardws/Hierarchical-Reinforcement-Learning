# -*- coding: UTF-8 -*-
"""
@Project ：Hierarchical-Reinforcement-Learning
@File    ：Config.py
@Author  ：Neardws
@Date    ：6/16/21 4:53 下午
"""
import numpy as np


class ExperimentConfig(object):
    """
    Object to hold the config requirements for an experiment
    :arg
        vehicle_number: number of sensor nodes
        data_types_number: number of data types in the system
        time_slots_number: number of time-slots in one experiment
        edge_views_number: number of edge views in the system
        communication_range: communication range of edge node
        transmission_power: transmission power of edge node
        bandwidth: bandwidth of edge node
        additive_white_gaussian_noise: additive white gaussian noise of transmission
        channel_fading_gain: channel fading gain of transmission
        path_loss_exponent: path loss exponent of transmission
        data_types_in_vehicles： data types in sensor node， which is randomly generated
        view_required_data： view required data at each time-slot， which is randomly generated
    """

    def __init__(self):
        """Map """
        self.longitude_min = None
        self.longitude_max = None
        self.latitude_min = None
        self.latitude_max = None

        self.time_start = None
        self.time_end = None

        """Experiment Setup"""
        self.episode_number = None
        self.max_episode_length = None

        """Some constant number"""
        self.vehicle_number = None
        self.data_types_number = None
        self.time_slots_number = None  # equal to max_episode_length
        self.edge_views_number = None

        self.seed_data_types_in_vehicles = None
        self.threshold_data_types_in_vehicles = None

        self.seed_data_size_of_types = None
        self.data_size_low_bound = None
        self.data_size_up_bound = None

        self.edge_view_required_start_time = None
        self.seed_edge_views_in_edge_node = None
        self.threshold_edge_views_in_edge_node = None

        self.seed_view_required_data = None
        self.threshold_view_required_data = None

        """The parameters related with transmission queue"""

        self.arrival_rate_low_bound = None
        self.arrival_rate_up_bound = None
        self.mean_service_time_of_types = None
        self.second_moment_service_time_of_types = None

        """The parameters related with wireless transmission"""
        self.communication_range = None
        self.transmission_power = None
        self.bandwidth = None
        self.additive_white_gaussian_noise = None
        self.mean_channel_fading_gain = None  # channel fading gain according to Gauss Distribution
        self.second_moment_channel_fading_gain = None
        self.path_loss_exponent = None

        self.noise_uncertainty_low_bound = None
        self.noise_uncertainty_up_bound = None

        self.trajectories_predicted_time = None

        self.rolling_score_window = None

        self.edge_node_x = None
        self.edge_node_y = None

        """Random generated value, the relationship of data types, edge views, vehicles, and edge node"""
        # self.data_size_of_types = None
        # self.data_types_in_vehicles = None
        # self.edge_views_in_edge_node = None
        # self.view_required_data = None
        # self.trajectories = None
        # self.data_in_edge_node = None

    def config(self,

               longitude_min=104.04565967220308,  # 104.05089219802858
               longitude_max=104.07650822204591,  # 104.082306230011
               latitude_min=30.654605745741608,  # 30.64253859556557
               latitude_max=30.68394513007631,  # 30.6684641634594

               time_start=1479031200,

               episode_number=5000,
               max_episode_length=300,

               vehicle_number=10,
               data_types_number=5,
               edge_views_number=10,

               threshold_data_types_in_vehicles=0.3,
               data_size_low_bound=300,  # Bytes
               data_size_up_bound=5 * 1024 * 1024,  # Bytes

               edge_view_required_start_time=10,
               threshold_edge_views_in_edge_node=0.3,
               threshold_view_required_data=0.3,

               arrival_rate_low_bound=None,
               arrival_rate_up_bound=None,
               mean_service_time_of_types=None,
               second_moment_service_time_of_types=None,

               communication_range=500,  # meters
               transmission_power=1,  # mW
               bandwidth=1,  # MHz
               additive_white_gaussian_noise=-70,  # dBm
               mean_channel_fading_gain=2,
               second_moment_channel_fading_gain=0.4,
               path_loss_exponent=3,

               noise_uncertainty_low_bound=0,  # dB
               noise_uncertainty_up_bound=3,  # dB
               trajectories_predicted_time=10,
               rolling_score_window=100,

               edge_node_x=1500,
               edge_node_y=1500
               ):
        """Map"""
        self.longitude_min = longitude_min
        self.longitude_max = longitude_max
        self.latitude_min = latitude_min
        self.latitude_max = latitude_max

        self.time_start = time_start

        """Experiment Setup"""
        self.episode_number = episode_number
        self.max_episode_length = max_episode_length

        self.time_end = time_start + max_episode_length

        """Some constant number"""
        self.vehicle_number = vehicle_number
        self.data_types_number = data_types_number
        self.time_slots_number = max_episode_length  # equal to max_episode_length
        self.edge_views_number = edge_views_number

        self.seed_data_types_in_vehicles = np.random.randint(0, 2 ** 32 - 2)
        self.threshold_data_types_in_vehicles = threshold_data_types_in_vehicles

        self.seed_data_size_of_types = np.random.randint(0, 2 ** 32 - 2)
        self.data_size_low_bound = data_size_low_bound
        self.data_size_up_bound = data_size_up_bound

        self.seed_edge_views_in_edge_node = np.random.randint(0, 2 ** 32 - 2)
        self.edge_view_required_start_time = edge_view_required_start_time,
        self.threshold_edge_views_in_edge_node = threshold_edge_views_in_edge_node

        self.seed_view_required_data = np.random.randint(0, 2 ** 32 - 2)
        self.threshold_view_required_data = threshold_view_required_data

        """The parameters related with transmission queue"""

        self.arrival_rate_low_bound = arrival_rate_low_bound
        self.arrival_rate_up_bound = arrival_rate_up_bound
        self.mean_service_time_of_types = mean_service_time_of_types
        self.second_moment_service_time_of_types = second_moment_service_time_of_types

        """The parameters related with wireless transmission"""
        self.communication_range = communication_range
        self.transmission_power = transmission_power
        self.bandwidth = bandwidth
        self.additive_white_gaussian_noise = additive_white_gaussian_noise
        self.mean_channel_fading_gain = mean_channel_fading_gain  # channel fading gain according to Gauss Distribution
        self.second_moment_channel_fading_gain = second_moment_channel_fading_gain
        self.path_loss_exponent = path_loss_exponent

        self.noise_uncertainty_low_bound = noise_uncertainty_low_bound
        self.noise_uncertainty_up_bound = noise_uncertainty_up_bound

        self.trajectories_predicted_time = trajectories_predicted_time
        self.rolling_score_window = rolling_score_window

        self.edge_node_x = edge_node_x
        self.edge_node_y = edge_node_y


class AgentConfig(object):
    """
    Object to hold the config requirements for an agent/game
    :arg
        seed: seed for random number, to make sure the result can be recurrent
        environment: environment where agent interact with
        requirement_to_solve_game: # TODO fix the meaning
        num_episodes_to_run: the number of episodes
        file_to_save_data_results: file to save the result
        file_to_save_results_graph: # TODO may need more graph for the experiment
        runs_per_agents: #TODO Fix the meaning
        visualise_overall_results: show the overall results or not
        visualise_individual_results: show the results individual or not
        hyperparameters: the parameters of NN, neural network
        use_GPU: is the data on the GPU, select devices to run
        overwrite_existing_results_file: overwrite the result file or not
        save_model: save the model or not
        standard_deviation_results: # TODO fix the meaning
        randomise_random_seed: # TODO fix the meaning
        show_solution_score: show the solution score or not
        debug_mode: in debug mode or not
    """

    def __init__(self):
        self.experience_replay_buffer_buffer_size = None
        self.experience_replay_buffer_batch_size = None
        self.experience_replay_buffer_seed = None

        self.reward_replay_buffer_buffer_size = None
        self.reward_replay_buffer_batch_size = None
        self.reward_replay_buffer_seed = None

        self.use_gpu = None

        self.nn_seed = None

        self.environment_seed = None

        self.hyperparameters = None

        self.file_to_save_data_results = None

    def config(self,
               experience_replay_buffer_buffer_size=30000,
               experience_replay_buffer_batch_size=256,
               experience_replay_buffer_seed=np.random.randint(0, 2 ** 32 - 2),
               reward_replay_buffer_buffer_size=30000,
               reward_replay_buffer_batch_size=256,
               reward_replay_buffer_seed=np.random.randint(0, 2 ** 32 - 2),
               use_gpu=True,
               noise_action_size=None,
               noise_seed=np.random.randint(0, 2 ** 32 - 2),
               noise_mu=0.0,
               noise_theta=0.15,
               noise_sigma=0.25,
               nn_seed=np.random.randint(0, 2 ** 32 - 2),
               environment_seed=np.random.randint(0, 2 ** 32 - 2),
               hyperparameters=None,
               file_to_save_data_results="Results/HMAIMD_RESULTS.pkl"):
        self.experience_replay_buffer_buffer_size = experience_replay_buffer_buffer_size
        self.experience_replay_buffer_batch_size = experience_replay_buffer_batch_size
        self.experience_replay_buffer_seed = experience_replay_buffer_seed
        self.reward_replay_buffer_buffer_size = reward_replay_buffer_buffer_size
        self.reward_replay_buffer_batch_size = reward_replay_buffer_batch_size
        self.reward_replay_buffer_seed = reward_replay_buffer_seed
        self.use_gpu = use_gpu
        self.noise_action_size = noise_action_size
        self.noise_seed = noise_seed
        self.noise_mu = noise_mu
        self.noise_theta = noise_theta
        self.noise_sigma = noise_sigma
        self.nn_seed = nn_seed
        self.environment_seed = environment_seed
        self.hyperparameters = hyperparameters
        self.file_to_save_data_results = file_to_save_data_results


if __name__ == '__main__':
    # np.random.seed(1)
    # print(np.random.rand(10))
    # np.random.seed(1)
    # print(np.random.rand(10))
    # print(np.random.randint(0,2,10))
    # print(np.random.randint(0,2,10))

    # TODO test this code
    action_time_of_sensor_nodes = np.zeros((2, 3))
    print(action_time_of_sensor_nodes.shape)
    print(action_time_of_sensor_nodes)
    action_time_of_sensor_nodes[:, 0] = 1
    print(action_time_of_sensor_nodes)
