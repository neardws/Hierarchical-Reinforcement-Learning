# -*- coding: UTF-8 -*-
"""
@Project ：Hierarchical-Reinforcement-Learning 
@File    ：DDPG_Agent.py
@Author  ：Neardws
@Date    ：9/7/21 2:35 下午 
"""
import torch
import numpy as np
from Environments.VehicularNetworkEnv.envs.VehicularNetworkEnv import VehicularNetworkEnv
from Exploration_strategies.Gaussian_Exploration import Gaussian_Exploration
from nn_builder.pytorch.NN import NN
from torch import optim
from tqdm import tqdm


class DDPG_Agent(object):
    def __init__(self, environment: VehicularNetworkEnv):
        self.environment = environment
        self.done = None
        self.reward = None
        self.action = None
        self.hyperparameters = None
        self.config = None
        _, _, self.reward_observation = self.environment.reset()
        self.total_episode_score_so_far = 0
        self.device = "cuda" if self.environment.config.use_gpu else "cpu"

        self.replay_buffer = DDPG_ReplayBuffer(
            buffer_size=self.config.replay_buffer_buffer_size,
            batch_size=self.config.replay_buffer_batch_size,
            seed=self.config.replay_buffer_seed
        )

        self.action_size = self.environment.get_sensor_action_size() * self.environment.config.vehicle_number + self.environment.get_edge_action_size()
        self.sensor_exploration_strategy = Gaussian_Exploration(size=self.action_size,
                                                                hyperparameters=self.hyperparameters,
                                                                key_to_use="Actor_of_DDPG")

        self.actor_local_of_ddpg = self.create_nn(
            input_dim=self.environment.get_actor_input_size_for_reward(),
            output_dim=self.action_size,
            key_to_use="Actor_of_DDPG"
        )

        self.actor_target_of_ddpg = self.create_nn(
            input_dim=self.environment.get_actor_input_size_for_reward(),
            output_dim=self.action_size,
            key_to_use="Actor_of_DDPG"
        )

        DDPG_Agent.copy_model_over(from_model=self.actor_local_of_ddpg,
                                   to_model=self.actor_target_of_ddpg)

        self.actor_optimizer_of_ddpg = optim.Adam(
            params=self.actor_local_of_ddpg.parameters(),
            lr=self.hyperparameters["Actor_of_DDPG"]["learning_rate"],
            eps=1e-8
        )

        optim.lr_scheduler.ReduceLROnPlateau(self.actor_optimizer_of_ddpg, mode='min', factor=0.1,
                                             patience=10, verbose=False, threshold=0.0001, threshold_mode='rel',
                                             cooldown=0, min_lr=0, eps=1e-08)

        self.critic_local_of_ddpg = self.create_nn(
            input_dim=self.environment.get_actor_input_size_for_reward() + self.action_size,
            output_dim=1,
            key_to_use="Critic_of_DDPG"
        )

        self.critic_target_of_ddpg = self.create_nn(
            input_dim=self.environment.get_actor_input_size_for_reward() + self.action_size,
            output_dim=1,
            key_to_use="Critic_of_DDPG"
        )

        DDPG_Agent.copy_model_over(from_model=self.critic_local_of_ddpg,
                                   to_model=self.critic_target_of_ddpg)

        self.critic_optimizer_of_edge_node = optim.Adam(
            params=self.critic_local_of_ddpg.parameters(),
            lr=self.hyperparameters["Critic_of_DDPG"]["learning_rate"],
            eps=1e-8
        )

        optim.lr_scheduler.ReduceLROnPlateau(self.critic_optimizer_of_edge_node, mode='min', factor=0.1,
                                             patience=10, verbose=False, threshold=0.0001, threshold_mode='rel',
                                             cooldown=0, min_lr=0, eps=1e-08)

    def step(self):
        with tqdm(total=self.environment.max_episode_length) as my_bar:
            while not self.done:
                self.pick_actions()
                self.conduct_action()
                self.save_experience()
                if self.time_for_learn():
                    self.DDPG_ReplayBuffer.sample()
                    self.actor_and_critic_to_learn()
                my_bar.update(n=1)

    def pick_actions(self):
        state = self.observation.unsqueeze(0).float().to(self.device)
        self.actor_local_of_ddpg.eval()
        with torch.no_grad():
            action = self.actor_local_of_ddpg(state)
        self.actor_local_of_ddpg.train()
        self.action = action

    def conduct_action(self):

        priority = np.zeros(shape=(self.environment.config.vehicle_number, self.environment.config.data_types_number),
                            dtype=np.float)
        arrival_rate = np.zeros(
            shape=(self.environment.config.vehicle_number, self.environment.config.data_types_number), dtype=np.float)

        for sensor_node_index in range(self.environment.config.vehicle_number):
            start_index = sensor_node_index * 2 * self.environment.config.data_types_number
            sensor_node_action = self.action[0][start_index, start_index + 2 * self.environment.config.data_types_number]
            sensor_node_action_of_priority = \
                sensor_node_action[0:self.environment.config.data_types_number]  # first data types are priority
            sensor_node_action_of_arrival_rate = \
                sensor_node_action[
                self.environment.config.data_types_number:]  # second data types number are arrival rate

            for data_type_index in range(self.environment.config.data_types_number):
                if self.environment.state["data_types"][sensor_node_index][data_type_index] == 1:
                    priority[sensor_node_index][data_type_index] = sensor_node_action_of_priority[data_type_index]

                    arrival_rate[sensor_node_index][data_type_index] = \
                        float(sensor_node_action_of_arrival_rate[data_type_index]) / \
                        self.environment.config.mean_service_time_of_types[sensor_node_index][data_type_index]

        edge_nodes_bandwidth = self.action[0][-self.environment.config.data_types_number:-1].cpu().data.numpy() * self.environment.config.bandwidth

        self.action = {"priority": priority,
                       "arrival_rate": arrival_rate,
                       "bandwidth": edge_nodes_bandwidth}

    def save_experience(self):
        if self.replay_buffer is None:
            raise Exception("Buffer is None")
        self.replay_buffer.add_experience(
            obeservation=self.observation,
            action=self.action,
            reward=self.reward,
            next_observation=self.next_observation,
            done=self.done
        )

    def time_for_learn(self):
        return len(self.replay_buffer) > (
                self.config.buffer_batch_size * self.config.hyperparameters[
            "learning_updates_per_learning_session"]) and \
               self.environment.episode_step % self.hyperparameters["update_every_n_steps"] == 0

    def actor_and_critic_to_learn(self, observations, actions, rewards, next_observations, dones):
        actions_predicted = self.actor_local_of_ddpg(self.observation)

        actor_loss = -self.critic_local_of_ddpg(
            torch.cat((observations, actions_predicted), dim=1).mean()
        )
        self.take_optimisation_step(self.actor_optimizer_of_ddpg,
                                    self.actor_local_of_ddpg,
                                    actor_loss,
                                    self.hyperparameters["Actor_of_DDPG"]["gradient_clipping_norm"])

    def create_nn(self, input_dim, output_dim, key_to_use=None, override_seed=None, hyperparameters=None):
        """
        Creates a neural network for the agents to use
        :param input_dim: input dimension
        :param output_dim: output dimension
        :param key_to_use:
        :param override_seed:
        :param hyperparameters:
        :return:
        """
        if hyperparameters is None:
            hyperparameters = self.hyperparameters
        if key_to_use:
            hyperparameters = hyperparameters[key_to_use]
        if override_seed:
            seed = override_seed
        else:
            seed = self.config.nn_seed

        default_hyperparameter_choices = {"output_activation": None,
                                          "hidden_activations": "relu",
                                          "dropout": 0.5,
                                          "initialiser": "default",
                                          "batch_norm": False,
                                          "columns_of_data_to_be_embedded": [],
                                          "embedding_dimensions": [],
                                          "y_range": ()}

        for key in default_hyperparameter_choices:
            if key not in hyperparameters.keys():
                hyperparameters[key] = default_hyperparameter_choices[key]

        """Creates a PyTorch neural network
           Args:
               - input_dim: Integer to indicate the dimension of the input into the network
               - layers_info: List of integers to indicate the width and number of linear layers you want in your 
               network,
                 e.g. [5, 8, 1] would produce a network with 3 linear layers of width 5, 8 and then 1
               - hidden_activations: String or list of string to indicate the activations you want used on the output 
               of hidden layers (not including the output layer). Default is ReLU.
               - output_activation: String to indicate the activation function you want the output to go through.
                Provide a list of strings if you want multiple output heads
               - dropout: Float to indicate what dropout probability you want applied after each hidden layer
               - initialiser: String to indicate which initialiser you want used to initialise all the parameters. 
               All PyTorch initialisers are supported. PyTorch's default initialisation is the default.
               - batch_norm: Boolean to indicate whether you want batch norm applied to the output of every hidden layer
               . Default is False
               - columns_of_data_to_be_embedded: List to indicate the columns numbers of the data that you want to 
               be put through an embedding layer before being fed through the other layers of the network. 
               Default option is no embeddings
               - embedding_dimensions: If you have categorical variables you want embedded before flowing 
               through the network then you specify the embedding dimensions here with a list like so: 
               [ [embedding_input_dim_1, embedding_output_dim_1],
               [embedding_input_dim_2, embedding_output_dim_2] ...]. Default is no embeddings
               - y_range: Tuple of float or integers of the form (y_lower, y_upper) indicating the range 
               you want to restrict the output values to in regression tasks. Default is no range restriction
               - random_seed: Integer to indicate the random seed you want to use
        """
        return NN(input_dim=input_dim,
                  layers_info=hyperparameters["linear_hidden_units"] + [output_dim],
                  output_activation=hyperparameters["final_layer_activation"],
                  batch_norm=hyperparameters["batch_norm"],
                  dropout=hyperparameters["dropout"],
                  hidden_activations=hyperparameters["hidden_activations"],
                  initialiser=hyperparameters["initialiser"],
                  columns_of_data_to_be_embedded=hyperparameters["columns_of_data_to_be_embedded"],
                  embedding_dimensions=hyperparameters["embedding_dimensions"],
                  y_range=hyperparameters["y_range"],
                  random_seed=seed).to(self.device)

    @staticmethod
    def copy_model_over(from_model, to_model):
        """Copies model parameters from from_model to to_model"""
        for to_model, from_model in zip(to_model.parameters(), from_model.parameters()):
            to_model.data.copy_(from_model.data.clone())
