# -*- coding: UTF-8 -*-
"""
@Project ：Hierarchical-Reinforcement-Learning 
@File    ：HMAIMD.py
@Author  ：Neardws
@Date    ：7/1/21 9:49 上午 
"""
import numpy as np
import torch
import torch.nn.functional as functional
from torch import optim, Tensor
from nn_builder.pytorch.NN import NN  # construct a neural network via PyTorch
from Utilities.Data_structures.Config import Agent_Config
from Utilities.Data_structures.Replay_Buffer import Replay_Buffer
from Exploration_strategies.OU_Noise_Exploration import OU_Noise_Exploration
from Environments.VehicularNetworkEnv.envs.VehicularNetworkEnv import VehicularNetworkEnv


class HMAIMD_Agent(object):
    """

    """

    def __init__(self, agent_config=Agent_Config(), environment=VehicularNetworkEnv()):
        self.config = agent_config
        self.environment = environment
        self.hyperparameters = self.config.hyperparameters

        self.state = self.environment.reset()
        self.sensor_observations = None
        self.edge_observation = None
        self.next_state = None
        self.reward = None
        self.done = False

        self.action = None
        self.sensor_actions = None
        self.edge_action = None
        self.reward_action = None

        """
        Some parameters
        """
        self.total_episode_score_so_far = 0
        self.game_full_episode_scores = []
        self.rolling_results = []
        self.max_rolling_score_seen = float("-inf")
        self.max_episode_score_seen = float("-inf")
        self.episode_index = 0
        self.episode_step = 0
        self.device = "cuda" if self.config.use_GPU else "cpu"
        self.turn_off_exploration = False

        """
        ______________________________________________________________________________________________________________
        Replay Buffer and Exploration Strategy
        ______________________________________________________________________________________________________________
        """

        """Experience Replay Buffer"""
        self.experience_replay_buffer = Replay_Buffer(buffer_size=self.config.experience_replay_buffer_buffer_size,
                                                      batch_size=self.config.experience_replay_buffer_batch_size,
                                                      seed=self.config.experience_replay_buffer_seed)

        """Reward Replay Buffer"""
        self.reward_replay_buffer = Replay_Buffer(buffer_size=self.config.reward_replay_buffer_buffer_size,
                                                  batch_size=self.config.reward_replay_buffer_batch_size,
                                                  seed=self.config.reward_replay_buffer_seed)

        """Exploration Strategy"""
        self.exploration_strategy = OU_Noise_Exploration(self.config)

        """
        ______________________________________________________________________________________________________________
        Replay Buffer and Exploration Strategy End
        ______________________________________________________________________________________________________________
        """

        """
        ______________________________________________________________________________________________________________
        Actor network and Critic network
        ______________________________________________________________________________________________________________
        """

        """Actor Network of Sensor Nodes"""
        self.sensor_observations_size = self.environment.get_sensor_observations_size()
        self.sensor_action_size = self.environment.get_sensor_action_size()
        self.actor_local_of_sensor_nodes = [
            self.create_NN_for_actor_network_of_sensor_node(
                input_dim=self.sensor_observations_size,
                output_dim=self.sensor_action_size
            ) for _ in range(self.environment.vehicle_number)
        ]

        self.actor_target_of_sensor_nodes = [
            self.create_NN_for_actor_network_of_sensor_node(
                input_dim=self.sensor_observations_size,
                output_dim=self.sensor_action_size
            ) for _ in range(self.environment.vehicle_number)
        ]

        for index in range(self.environment.vehicle_number):
            HMAIMD_Agent.copy_model_over(from_model=self.actor_local_of_sensor_nodes[index],
                                         to_model=self.actor_target_of_sensor_nodes[index])
        self.actor_optimizer_of_sensor_nodes = [
            optim.Adam(params=self.actor_local_of_sensor_nodes[index].parameters(),
                       lr=self.hyperparameters['actor_of_sensor']['learning_rate'],
                       eps=1e-4
                       ) for index in range(self.environment.vehicle_number)
        ]

        """Critic Network of Sensor Nodes"""
        self.critic_size_for_sensor = self.environment.get_critic_size_for_sensor()
        self.critic_local_of_sensor_nodes = [
            self.create_NN_for_critic_network_of_sensor_node(
                input_dim=self.critic_size_for_sensor,
                output_dim=1
            ) for _ in range(self.environment.vehicle_number)
        ]

        self.critic_target_of_sensor_nodes = [
            self.create_NN_for_critic_network_of_sensor_node(
                input_dim=self.critic_size_for_sensor,
                output_dim=1
            ) for _ in range(self.environment.vehicle_number)
        ]

        for index in range(self.environment.vehicle_number):
            HMAIMD_Agent.copy_model_over(from_model=self.critic_local_of_sensor_nodes[index],
                                         to_model=self.critic_target_of_sensor_nodes[index])
        self.critic_optimizer_of_sensor_nodes = [
            optim.Adam(params=self.critic_local_of_sensor_nodes[index].parameters(),
                       lr=self.hyperparameters['critic_of_sensor']['learning_rate'],
                       eps=1e-4
                       ) for index in range(self.environment.vehicle_number)
        ]

        """Actor Network for Edge Node"""
        self.actor_local_of_edge_node = self.create_NN_for_actor_network_of_edge_node(
            input_dim=self.environment.get_actor_input_size_for_edge(),
            output_dim=self.environment.get_edge_action_size()
        )
        self.actor_target_of_edge_node = self.create_NN_for_actor_network_of_edge_node(
            input_dim=self.environment.get_actor_input_size_for_edge(),
            output_dim=self.environment.get_edge_action_size()
        )
        HMAIMD_Agent.copy_model_over(from_model=self.actor_local_of_edge_node,
                                     to_model=self.actor_target_of_edge_node)
        self.actor_optimizer_of_edge_node = optim.Adam(
            params=self.actor_local_of_edge_node.parameters(),
            lr=self.hyperparameters['actor_of_edge']['learning_rate'],
            eps=1e-4
        )

        """Critic Network for Edge Node"""
        self.critic_local_of_edge_node = self.create_NN_for_critic_network_of_edge_node(
            input_dim=self.environment.get_critic_size_for_edge(),
            output_dim=1
        )
        self.critic_target_of_edge_node = self.create_NN_for_critic_network_of_edge_node(
            input_dim=self.environment.get_critic_size_for_edge(),
            output_dim=1
        )
        HMAIMD_Agent.copy_model_over(from_model=self.critic_local_of_edge_node,
                                     to_model=self.critic_target_of_edge_node)
        self.critic_optimizer_of_edge_node = optim.Adam(
            params=self.critic_local_of_edge_node.parameters(),
            lr=self.hyperparameters['critic_of_edge_node']['learning_rate'],
            eps=1e-4
        )

        """Actor Network for Reward Function"""
        self.actor_local_of_reward_function = self.create_NN_for_actor_network_of_reward_function(
            input_dim=self.environment.get_actor_input_size_for_reward(),
            output_dim=self.environment.get_reward_action_size()
        )
        self.actor_target_of_reward_function = self.create_NN_for_actor_network_of_reward_function(
            input_dim=self.environment.get_actor_input_size_for_reward(),
            output_dim=self.environment.get_reward_action_size()
        )
        HMAIMD_Agent.copy_model_over(from_model=self.actor_local_of_reward_function,
                                     to_model=self.actor_target_of_reward_function)
        self.actor_optimizer_of_reward_function = optim.Adam(
            params=self.actor_local_of_reward_function.parameters(),
            lr=self.hyperparameters['actor_of_reward_function']['learning_rate'],
            eps=1e-4
        )

        """Critic Network for Reward Function"""
        self.critic_local_of_reward_function = self.create_NN_for_critic_network_of_reward_function(
            input_dim=self.environment.get_critic_size_for_reward(),
            output_dim=1
        )
        self.critic_target_of_reward_function = self.create_NN_for_critic_network_of_reward_function(
            input_dim=self.environment.get_critic_size_for_reward(),
            output_dim=1
        )
        HMAIMD_Agent.copy_model_over(from_model=self.critic_local_of_reward_function,
                                     to_model=self.critic_target_of_reward_function)
        self.critic_optimizer_of_reward_function = optim.Adam(
            params=self.critic_local_of_reward_function.parameters(),
            lr=self.hyperparameters['critic_of_reward_function']['learning_rate'],
            eps=1e-4
        )

        """
        ______________________________________________________________________________________________________________
        Actor network and Critic network End
        ______________________________________________________________________________________________________________
        """

    @staticmethod
    def copy_model_over(from_model, to_model):
        """Copies model parameters from from_model to to_model"""
        for to_model, from_model in zip(to_model.parameters(), from_model.parameters()):
            to_model.data.copy_(from_model.data.clone())

    """
    ______________________________________________________________________________________________________________
    Create Neural Network for Actor and Critic Network
    ______________________________________________________________________________________________________________
    """

    def create_NN_for_actor_network_of_sensor_node(self, input_dim, output_dim,
                                                   hyperparameters=None):  # the structure of network is different from other actor networks
        return NN(input_dim=input_dim)

    def create_NN_for_critic_network_of_sensor_node(self, input_dim, output_dim,
                                                    hyperparameters=None):  # the structure of network is different from other actor networks
        return NN(input_dim=input_dim)

    def create_NN_for_actor_network_of_edge_node(self, input_dim, output_dim, hyperparameters=None):
        return NN(input_dim=input_dim)

    def create_NN_for_critic_network_of_edge_node(self, input_dim, output_dim, hyperparameters=None):
        return NN(input_dim=input_dim)

    def create_NN_for_actor_network_of_reward_function(self, input_dim, output_dim, hyperparameters=None):
        return NN(input_dim=input_dim)

    def create_NN_for_critic_network_of_reward_function(self, input_dim, output_dim, hyperparameters=None):
        return NN(input_dim=input_dim)

    """
    ______________________________________________________________________________________________________________
    Create Neural Network for Actor and Critic Network End
    ______________________________________________________________________________________________________________
    """

    """
    Workflow of each step of HMAIMD_Agent
    No.1 If action time of sensor node equal to now time , 
         then Actor of each sensor node to pick an action according to sensor observation
    No.2 Actor of edge node to pick an action according to edge observation and action of sensor nodes
    No.3 Combine action of sensor nodes and edge node into one global action
    No.4 Conduct global action to environment and get return with next_state, reward and etc.
    No.5 Actor of reward function to pick an action according to global state and global action
    No.6 Save experiences into experiences replay buffer
    No.7 Save reward experiences into reward reward buffer
    No.8 If time to learn, sample from experiences
    No.9 Train each critic target network and actor target network
    
    """

    def step(self):
        """Runs a step in the game"""
        while not self.done:  # when the episode is not over
            self.sensor_actions = self.sensor_nodes_pick_actions()  # sensor nodes pick actions
            self.edge_action = self.edge_node_pick_action()
            self.global_action = self.combined_action()
            self.conduct_action()
            self.reward_action = self.reward_function_pick_action()
            self.save_experience()
            self.save_reward_experience()
            if self.time_for_critic_and_actor_of_sensor_nodes_and_edge_node_to_learn():
                for _ in range(self.hyperparameters["learning_updates_per_learning_session"]):

                    sensor_nodes_observations, edge_node_observations, sensor_actions, edge_actions, sensor_nodes_rewards, \
                    edge_node_rewards, next_sensor_nodes_observations, next_edge_node_observations, dones = self.sample_experiences(
                        "experience_replay_buffer")

                    self.sensor_nodes_and_edge_node_to_learn(sensor_nodes_observations=sensor_nodes_observations,
                                                             edge_node_observations=edge_node_observations,
                                                             sensor_actions=sensor_actions,
                                                             edge_actions=edge_actions,
                                                             sensor_nodes_rewards=sensor_nodes_rewards,
                                                             edge_node_rewards=edge_node_rewards,
                                                             next_sensor_nodes_observations=next_sensor_nodes_observations,
                                                             next_edge_node_observations=next_edge_node_observations,
                                                             dones=dones)

            if self.time_for_critic_and_actor_of_reward_function_to_learn():
                for _ in range(self.hyperparameters["learning_updates_per_learning_session"]):
                    states, actions, rewards, next_states, dones = self.sample_experiences("reward_replay_buffer")
                    self.reward_function_learn()
            self.state = self.next_state  # this is to set the state for the next iteration
            self.episode_step += 1
        self.episode_index += 1

    def sample_experiences(self, buffer_name):
        if buffer_name == "experience_replay_buffer":
            return self.experience_replay_buffer.sample()
        elif buffer_name == "reward_replay_buffer":
            return self.reward_replay_buffer.sample()
        else:
            raise Exception("Buffer name is Wrong")

    def sensor_nodes_pick_actions(self, sensor_nodes_observation):
        """Picks an action using the actor network of each sensor node
        and then adds some noise to it to ensure exploration"""
        for sensor_node_index in range(self.environment.vehicle_number):
            if self.state['action_time'][sensor_node_index][self.episode_index] == 1:
                sensor_node_observation = sensor_nodes_observation[sensor_node_index, :]
                self.actor_local_of_sensor_nodes[sensor_node_index].eval()  # set the model to evaluation state
                with torch.no_grad():  # do not compute the gradient
                    sensor_action = self.actor_local_of_sensor_nodes[sensor_node_index](
                        sensor_node_observation).cpu().data.numpy()
                self.actor_local_of_sensor_nodes[sensor_node_index].train()  # set the model to training state
                sensor_action = self.exploration_strategy.perturb_action_for_exploration_purposes(
                    {"action": sensor_action})
                self.sensor_actions[sensor_node_index] = sensor_action

    def edge_node_pick_action(self, edge_observation, sensor_nodes_actions):
        edge_node_state = torch.cat((edge_observation, sensor_nodes_actions), 1)
        self.actor_local_of_edge_node.eval()
        with torch.no_grad():
            edge_action = self.actor_local_of_edge_node(edge_node_state).cpu().data.numpy()
        self.actor_local_of_edge_node.train()
        edge_action = self.exploration_strategy.perturb_action_for_exploration_purposes({"action": edge_action})
        self.edge_action = edge_action

    def combined_action(self):

        pass

    def conduct_action(self):
        """Conducts an action in the environment"""
        self.next_state, self.reward, self.done, _ = self.environment.step(self.action)
        self.total_episode_score_so_far += self.reward
        # TODO what is clip_rewards
        if self.hyperparameters["clip_rewards"]:
            self.reward = max(min(self.reward, 1.0), -1.0)

    def reward_function_pick_action(self):
        reward_function_state = torch.from_numpy(self.reward_observation).float().unsqueeze(0).to(self.device)
        self.actor_local_of_reward_function.eval()
        with torch.no_grad():
            reward_function_action = self.actor_local_of_reward_function(reward_function_state).cpu().data.numpy()
        self.actor_local_of_reward_function.train()
        reward_function_action = self.exploration_strategy.perturb_action_for_exploration_purposes(
            {"action": reward_function_action})
        self.reward_action = reward_function_action

    def save_experience(self):

        # TODO Renew structure of experience and replay buffer
        """
        sensor_nodes_observations=torch.empty(), sensor_actions=torch.empty(),
                           sensor_nodes_rewards=torch.empty(), next_sensor_nodes_observations=torch.empty(),
                           dones=torch.empty()
        Saves the recent experience to the experience replay buffer
        :param memory: Buffer
        :param experience: self.state, self.action, self.reward, self.next_state, self.done
        :return: None
        """
        if self.experience_replay_buffer is None:
            raise Exception("experience_replay_buffer is None, function save_experience at HMAIMD.py")
        experience = self.sensor_nodes_observations, self.sensor_actions, self.sensor_nodes_rewards, self.next_sensor_nodes_observations, self.done
        self.experience_replay_buffer.add_experience(*experience)

    def save_reward_experience(self):
        if self.reward_replay_buffer is None:
            raise Exception("reward_replay_buffer is None, function save_experience at HMAIMD.py")
        reward_experience = self.last_state, self.last_action, self.last_reward_action, self.reward, self.state, self.action
        self.reward_replay_buffer.add_experience(*reward_experience)

    def time_for_critic_and_actor_of_sensor_nodes_and_edge_node_to_learn(self):
        """Returns boolean indicating whether there are enough experiences to learn from
        and it is time to learn for the actor and critic of sensor nodes and edge node"""
        return len(self.experience_replay_buffer) > self.config.experience_replay_buffer_batch_size and \
               self.episode_step % self.hyperparameters["update_every_n_steps"] == 0

    def time_for_critic_and_actor_of_reward_function_to_learn(self):
        """Returns boolean indicating whether there are enough experiences to learn from
        and it is time to learn for the actor and critic of sensor nodes and edge node"""
        return len(self.experience_replay_buffer) > self.config.reward_replay_buffer_batch_size and \
               self.episode_step % self.hyperparameters["update_every_n_steps"] == 0

    def sensor_nodes_and_edge_node_to_learn(self, sensor_nodes_observations=torch.empty(),
                                            edge_node_observations=torch.empty(),
                                            sensor_actions=torch.empty(), edge_actions=torch.empty(),
                                            sensor_nodes_rewards=torch.empty(), edge_node_rewards=torch.empty(),
                                            next_sensor_nodes_observations=torch.empty(),
                                            next_edge_node_observations=torch.empty(),
                                            dones=torch.empty()):

        sensor_nodes_actions_next_list = [
            self.actor_target_of_sensor_nodes[sensor_node_index](next_sensor_node_observations)
            for sensor_node_index, next_sensor_node_observations in enumerate(next_sensor_nodes_observations)]

        sensor_nodes_actions_next_tensor = torch.cat(
            (sensor_nodes_actions_next_list[0], sensor_nodes_actions_next_list[1]), 0)
        for index, sensor_nodes_actions_next in enumerate(sensor_nodes_actions_next_list):
            if index > 1:
                sensor_nodes_actions_next_tensor = torch.cat(
                    (sensor_nodes_actions_next_tensor, sensor_nodes_actions_next), 0)

        for sensor_node_index in range(self.environment.vehicle_number):
            sensor_node_observations = sensor_nodes_observations[sensor_node_index, :]
            sensor_node_rewards = sensor_nodes_rewards[sensor_node_index, :]
            next_sensor_node_observations = sensor_nodes_observations[sensor_node_index, :]

            """Runs a learning iteration for the critic"""
            """Computes the loss for the critic"""
            with torch.no_grad():
                critic_targets_next_of_sensor_node = self.critic_target_of_sensor_nodes[sensor_node_index](
                    torch.cat(next_sensor_node_observations, sensor_nodes_actions_next_tensor), 1)
                critic_targets_of_sensor_node = sensor_node_rewards + (
                            self.hyperparameters["discount_rate"] * critic_targets_next_of_sensor_node * (1.0 - dones))
            critic_expected_of_sensor_node = self.critic_local_of_sensor_nodes[sensor_node_index](
                torch.cat((sensor_node_observations, sensor_actions), 1))
            critic_loss_of_sensor_node: Tensor = functional.mse_loss(critic_expected_of_sensor_node,
                                                                     critic_targets_of_sensor_node)

            """Update target critic networks"""
            self.take_optimisation_step(self.critic_optimizer_of_sensor_nodes[sensor_node_index],
                                        self.critic_local_of_sensor_nodes[sensor_node_index],
                                        critic_loss_of_sensor_node,
                                        self.hyperparameters["critic_of_sensor"]["gradient_clipping_norm"])
            self.soft_update_of_target_network(self.critic_local_of_sensor_nodes[sensor_node_index],
                                               self.critic_target_of_sensor_nodes[sensor_node_index],
                                               self.hyperparameters["critic_of_sensor"]["tau"])

            """Runs a learning iteration for the actor"""
            if self.done:  # we only update the learning rate at end of each episode
                self.update_learning_rate(self.hyperparameters["actor_of_sensor"]["learning_rate"],
                                          self.actor_optimizer_of_sensor_nodes[sensor_node_index])
            """Calculates the loss for the actor"""
            actions_predicted_of_sensor_node = self.actor_local_of_sensor_nodes[sensor_node_index](
                sensor_node_observations)
            if sensor_node_index == 0:
                sensor_nodes_actions_add_actions_pred = torch.cat(
                    (actions_predicted_of_sensor_node, sensor_actions[1:self.environment.vehicle_number, :]), dim=1)
            elif sensor_node_index == self.environment.vehicle_number - 1:
                sensor_nodes_actions_add_actions_pred = torch.cat(
                    (sensor_actions[0:self.environment.vehicle_number - 1, :], actions_predicted_of_sensor_node), dim=1)
            else:
                sensor_nodes_actions_add_actions_pred = torch.cat((sensor_actions[0:sensor_node_index - 1, :],
                                                                   actions_predicted_of_sensor_node,
                                                                   sensor_actions[sensor_node_index + 1:self.environment.vehicle_number,
                                                                                 :]), dim=1)

            actor_loss_of_sensor_node = -self.critic_local_of_sensor_nodes[sensor_node_index](
                torch.cat((sensor_node_observations, sensor_nodes_actions_add_actions_pred), 1)).mean()

            self.take_optimisation_step(self.actor_optimizer_of_sensor_nodes[sensor_node_index],
                                        self.actor_local_of_sensor_nodes[sensor_node_index],
                                        actor_loss_of_sensor_node,
                                        self.hyperparameters["actor_of_sensor"]["gradient_clipping_norm"])
            self.soft_update_of_target_network(self.actor_local_of_sensor_nodes[sensor_node_index],
                                               self.actor_target_of_sensor_nodes[sensor_node_index],
                                               self.hyperparameters["actor_of_sensor"]["tau"])

        """Runs a learning iteration for the critic of edge node"""
        """Computes the loss for the critic"""
        with torch.no_grad():
            """Computes the critic target values to be used in the loss for the critic"""
            actions_next_of_edge_node = self.actor_target_of_edge_node(
                torch.cat((next_edge_node_observations, sensor_nodes_actions_next_tensor), dim=1))
            critic_targets_next_of_edge_node = self.critic_target_of_edge_node(
                torch.cat((next_edge_node_observations, sensor_nodes_actions_next_tensor, actions_next_of_edge_node),
                          dim=1))
            critic_targets_of_edge_node = edge_node_rewards + (
                    self.hyperparameters["discount_rate"] * critic_targets_next_of_edge_node * (1.0 - dones))

        critic_expected_of_edge_node = self.critic_local_of_edge_node(
            torch.cat((edge_node_observations, sensor_actions, edge_actions), 1))
        loss_of_edge_node = functional.mse_loss(critic_expected_of_edge_node, critic_targets_of_edge_node)
        self.take_optimisation_step(self.critic_optimizer_of_edge_node,
                                    self.critic_local_of_edge_node,
                                    loss_of_edge_node,
                                    self.hyperparameters["critic_of_edge"]["gradient_clipping_norm"])
        self.soft_update_of_target_network(self.critic_local_of_edge_node, self.critic_target_of_edge_node,
                                           self.hyperparameters["critic_of_edge"]["tau"])

        """Runs a learning iteration for the actor of edge node"""
        if self.done:  # we only update the learning rate at end of each episode
            self.update_learning_rate(self.hyperparameters["actor_of_edge"]["learning_rate"],
                                      self.actor_optimizer_of_edge_node)
        """Calculates the loss for the actor"""
        actions_predicted_of_edge_node = self.actor_local_of_edge_node(
            torch.cat((edge_node_observations, sensor_actions), dim=1))
        actor_loss_of_edge_node = -self.critic_local_of_edge_node(
            torch.cat((edge_node_observations, sensor_actions, actions_predicted_of_edge_node), dim=1)).mean()
        self.take_optimisation_step(self.actor_optimizer_of_edge_node, self.actor_local_of_edge_node,
                                    actor_loss_of_edge_node,
                                    self.hyperparameters["actor_of_edge"]["gradient_clipping_norm"])
        self.soft_update_of_target_network(self.actor_local_of_edge_node, self.actor_target_of_edge_node,
                                           self.hyperparameters["actor_of_edge"]["tau"])

    def reward_function_to_learn(self, last_states=torch.empty(), last_actions=torch.empty(),
                              last_reward_actions=torch.empty(), rewards=torch.empty(),
                              states=torch.empty(), actions=torch.empty(), dones=torch.empty()):

        """Runs a learning iteration for the critic of reward function"""
        with torch.no_grad():
            reward_actions_next = self.actor_target_of_reward_function(torch.cat((states, actions), dim=1))
            critic_targets_next = self.critic_target_of_reward_function(torch.cat((states, actions, reward_actions_next), 1))
            critic_targets = rewards + (self.hyperparameters["discount_rate"] * critic_targets_next * (1.0 - dones))
        critic_expected = self.critic_local_of_reward_function(torch.cat((last_states, last_actions, last_reward_actions), 1))
        loss = functional.mse_loss(critic_expected, critic_targets)
        self.take_optimisation_step(self.critic_optimizer_of_reward_function,
                                    self.critic_local_of_reward_function, loss,
                                    self.hyperparameters["critic_of_reward"]["gradient_clipping_norm"])
        self.soft_update_of_target_network(self.critic_local_of_reward_function, self.critic_target_of_reward_function,
                                           self.hyperparameters["critic_of_reward"]["tau"])

        """Runs a learning iteration for the actor"""
        if self.done:  # we only update the learning rate at end of each episode
            self.update_learning_rate(self.hyperparameters["actor_of_reward"]["learning_rate"], self.actor_optimizer_of_reward_function)
        """Calculates the loss for the actor"""
        actions_predicted = self.actor_local_of_reward_function(torch.cat((last_actions, last_actions), dim=1))
        actor_loss = -self.critic_local_of_reward_function(torch.cat((last_actions, last_actions, actions_predicted), dim=1)).mean()
        self.take_optimisation_step(self.actor_optimizer_of_reward_function, self.actor_local_of_reward_function, actor_loss,
                                    self.hyperparameters["actor_of_reward"]["gradient_clipping_norm"])
        self.soft_update_of_target_network(self.actor_local_of_reward_function, self.actor_target_of_reward_function,
                                           self.hyperparameters["actor_of_reeard"]["tau"])


    def update_learning_rate(self, starting_lr, optimizer):
        """
        Lowers the learning rate according to how close we are to the solution
        The learning rate is smaller when closer the solution
        However, we must determine the average score required to win
        :param starting_lr:  learning rate of starting
        :param optimizer:
        :return:
        """
        new_lr = starting_lr
        if len(self.rolling_results) > 0:
            last_rolling_score = self.rolling_results[-1]
            if last_rolling_score > 0.75 * self.average_score_required_to_win:
                new_lr = starting_lr / 100.0
            elif last_rolling_score > 0.6 * self.average_score_required_to_win:
                new_lr = starting_lr / 20.0
            elif last_rolling_score > 0.5 * self.average_score_required_to_win:
                new_lr = starting_lr / 10.0
            elif last_rolling_score > 0.25 * self.average_score_required_to_win:
                new_lr = starting_lr / 2.0
            else:
                new_lr = starting_lr
            for g in optimizer.param_groups:
                g['lr'] = new_lr
        if np.random.random() < 0.001: self.logger.info("Learning rate {}".format(new_lr))

    def take_optimisation_step(self, optimizer, network, loss, clipping_norm=None, retain_graph=False):
        """Takes an optimisation step by calculating gradients given the loss and then updating the parameters"""
        if not isinstance(network, list): network = [network]
        optimizer.zero_grad()  # reset gradients to 0
        loss.backward(retain_graph=retain_graph)  # this calculates the gradients
        self.logger.info("Loss -- {}".format(loss.item()))
        if self.debug_mode: self.log_gradient_and_weight_information(network, optimizer)
        if clipping_norm is not None:
            for net in network:
                torch.nn.utils.clip_grad_norm_(net.parameters(),
                                               clipping_norm)  # clip gradients to help stabilise training
        optimizer.step()  # this applies the gradients

    def soft_update_of_target_network(self, local_model, target_model, tau):
        """
        Updates the target network in the direction of the local network but by taking a step size
        less than one so the target network's parameter values trail the local networks. This helps stabilise training
        :param local_model:
        :param target_model:
        :param tau:
        :return:
        """
        for target_param, local_param in zip(target_model.parameters(), local_model.parameters()):
            target_param.data.copy_(tau * local_param.data + (1.0 - tau) * target_param.data)
